from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union, Self
from darts.utils import _build_tqdm_iterator, _parallel_apply
from darts import TimeSeries
from loggers import logger
import pandas as pd

class MyTimeSeries(TimeSeries):
    @classmethod
    def from_group_dataframe(
        cls,
        df: pd.DataFrame,
        group_cols: Union[List[str], str],
        time_col: Optional[str] = None,
        value_cols: Optional[Union[List[str], str]] = None,
        static_cols: Optional[Union[List[str], str]] = None,
        fill_missing_dates: Optional[bool] = False,
        freq: Optional[Union[str, int]] = None,
        fillna_value: Optional[float] = None,
        drop_group_cols: Optional[Union[List[str], str]] = None,
        n_jobs: Optional[int] = 1,
        verbose: Optional[bool] = False,
    ) -> List[Self]:
        """
        Build a list of TimeSeries instances grouped by a selection of columns from a DataFrame.
        One column (or the DataFrame index) has to represent the time,
        a list of columns `group_cols` must be used for extracting the individual TimeSeries by groups,
        and a list of columns `value_cols` has to represent the values for the individual time series.
        Values from columns ``group_cols`` and ``static_cols`` are added as static covariates to the resulting
        TimeSeries objects. These can be viewed with `my_series.static_covariates`. Different to `group_cols`,
        `static_cols` only adds the static values but are not used to extract the TimeSeries groups.

        Parameters
        ----------
        df
            The DataFrame
        group_cols
            A string or list of strings representing the columns from the DataFrame by which to extract the
            individual TimeSeries groups.
        time_col
            The time column name. If set, the column will be cast to a pandas DatetimeIndex (if it contains
            timestamps) or a RangeIndex (if it contains integers).
            If not set, the DataFrame index will be used. In this case the DataFrame must contain an index that is
            either a pandas DatetimeIndex, a pandas RangeIndex, or a pandas Index that can be converted to a
            RangeIndex. Be aware that the index must represents the actual index of each individual time series group
            (can contain non-unique values). It is better if the index has no holes; alternatively setting
            `fill_missing_dates` can in some cases solve these issues (filling holes with NaN, or with the provided
            `fillna_value` numeric value, if any).
        value_cols
            A string or list of strings representing the value column(s) to be extracted from the DataFrame. If set to
            `None`, the whole DataFrame will be used.
        static_cols
            A string or list of strings representing static variable columns from the DataFrame that should be
            appended as static covariates to the resulting TimeSeries groups. Different to `group_cols`, the
            DataFrame is not grouped by these columns. Note that for every group, there must be exactly one
            unique value.
        fill_missing_dates
            Optionally, a boolean value indicating whether to fill missing dates (or indices in case of integer index)
            with NaN values. This requires either a provided `freq` or the possibility to infer the frequency from the
            provided timestamps. See :meth:`_fill_missing_dates() <TimeSeries._fill_missing_dates>` for more info.
        freq
            Optionally, a string or integer representing the frequency of the underlying index. This is useful in order
            to fill in missing values if some dates are missing and `fill_missing_dates` is set to `True`.
            If a string, represents the frequency of the pandas DatetimeIndex (see `offset aliases
            <https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases>`_ for more info on
            supported frequencies).
            If an integer, represents the step size of the pandas Index or pandas RangeIndex.
        fillna_value
            Optionally, a numeric value to fill missing values (NaNs) with.
        drop_group_cols
            Optionally, a string or list of strings with `group_cols` column(s) to exclude from the static covariates.
        n_jobs
            Optionally, an integer representing the number of parallel jobs to run. Behavior is the same as in the
            `joblib.Parallel` class.
        verbose
            Optionally, a boolean value indicating whether to display a progress bar.

        Returns
        -------
        List[TimeSeries]
            A list containing a univariate or multivariate deterministic TimeSeries per group in the DataFrame.
        """
        if time_col is None and df.index.is_monotonic_increasing:
            logger.warning(
                "UserWarning: `time_col` was not set and `df` has a monotonically increasing (time) index. This "
                "results in time series groups with non-overlapping (time) index. You can ignore this warning if the "
                "index represents the actual index of each individual time series group."
            )

        group_cols = [group_cols] if not isinstance(group_cols, list) else group_cols
        if drop_group_cols:
            drop_group_cols = (
                [drop_group_cols]
                if not isinstance(drop_group_cols, list)
                else drop_group_cols
            )
            invalid_cols = set(drop_group_cols) - set(group_cols)
            if invalid_cols:
                raise ValueError(
                        f"Found invalid `drop_group_cols` columns. All columns must be in the passed `group_cols`. "
                        f"Expected any of: {group_cols}, received: {invalid_cols}."
                    )
            drop_group_col_idx = [
                idx for idx, col in enumerate(group_cols) if col in drop_group_cols
            ]
        else:
            drop_group_cols = []
            drop_group_col_idx = []
        if static_cols is not None:
            static_cols = (
                [static_cols] if not isinstance(static_cols, list) else static_cols
            )
        else:
            static_cols = []
        static_cov_cols = group_cols + static_cols
        extract_static_cov_cols = [
            col for col in static_cov_cols if col not in drop_group_cols
        ]
        extract_time_col = [] if time_col is None else [time_col]

        if value_cols is None:
            value_cols = df.columns.drop(static_cov_cols + extract_time_col).tolist()
        extract_value_cols = [value_cols] if isinstance(value_cols, str) else value_cols

        df = df[static_cov_cols + extract_value_cols + extract_time_col]

        # sort on entire `df` to avoid having to sort individually later on
        if time_col:
            # 在这里修改了源代码，当time_col列为整数时，直接用整数索引，而不需要转换为pd.DatetimeIndex
            if pd.api.types.is_integer_dtype(df[time_col]):
                df.index = df[time_col]
            else:
                df.index = pd.DatetimeIndex(df[time_col])
            df = df.drop(columns=time_col)
        df = df.sort_index()

        groups = df.groupby(group_cols[0] if len(group_cols) == 1 else group_cols)

        iterator = _build_tqdm_iterator(
            groups,
            verbose=verbose,
            total=len(groups),
            desc="Creating TimeSeries",
        )

        def from_group(static_cov_vals, group):
            split = group[extract_value_cols]

            static_cov_vals = (
                (static_cov_vals,)
                if not isinstance(static_cov_vals, tuple)
                else static_cov_vals
            )
            # optionally, exclude group columns from static covariates
            if drop_group_col_idx:
                if len(drop_group_col_idx) == len(group_cols):
                    static_cov_vals = tuple()
                else:
                    static_cov_vals = tuple(
                        val
                        for idx, val in enumerate(static_cov_vals)
                        if idx not in drop_group_col_idx
                    )

            # check that for each group there is only one unique value per column in `static_cols`
            if static_cols:
                static_cols_valid = [
                    len(group[col].unique()) == 1 for col in static_cols
                ]
                if not all(static_cols_valid):
                    # encountered performance issues when evaluating the error message from below in every
                    # iteration with `raise_if_not(all(static_cols_valid), message, logger)`
                    invalid_cols = [
                        static_col
                        for static_col, is_valid in zip(static_cols, static_cols_valid)
                        if not is_valid
                    ]
                    raise ValueError(
                        f"Encountered more than one unique value in group {group} for given static columns: "
                        f"{invalid_cols}."
                    )
                # add the static covariates to the group values
                static_cov_vals += tuple(group[static_cols].values[0])

            return cls.from_dataframe(
                df=split,
                fill_missing_dates=fill_missing_dates,
                freq=freq,
                fillna_value=fillna_value,
                static_covariates=(
                    pd.DataFrame([static_cov_vals], columns=extract_static_cov_cols)
                    if extract_static_cov_cols
                    else None
                ),
            )

        return _parallel_apply(
            iterator,
            from_group,
            n_jobs,
            fn_args=dict(),
            fn_kwargs=dict(),
        )