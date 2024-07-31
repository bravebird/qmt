import torch
from pytorch_lightning.callbacks.early_stopping import EarlyStopping
from darts.utils.callbacks import TFMProgressBar
from torch.nn.modules.loss import MSELoss, CrossEntropyLoss
from pathlib2 import Path


work_dir = str(Path(__file__).parent.parent / "loggers/tsmixer_logs")
class ModelParameters:
    """模型参数"""

    def __init__(
            self,
            input_chunk_length=15, #13
            output_chunk_length=15,
            batch_size=32,
            full_training=True
    ):

        self.input_chunk_length = input_chunk_length  # lookback window
        self.output_chunk_length = output_chunk_length  # forecast/lookahead window
        self.batch_size = batch_size
        self.random_state = 42
        self.work_dir = work_dir

        # 第二个feed-forward层的隐藏层大小
        self.hidden_size = 64
        # The size of the first feed-forward layer in the feature mixing MLP.
        self.ff_size = 64
        # The number of mixer blocks in the model. The number includes the first block and all subsequent blocks.
        self.num_blocks = 2
        # The name of the activation function to use in the mixer layers. Default: “ReLU”.
        # Must be one of “ReLU”, “RReLU”, “PReLU”, “ELU”, “Softplus”, “Tanh”, “SELU”, “LeakyReLU”, “Sigmoid”, “GELU”.
        self.activation = 'ReLU'
        self.dropout = 0.1
        # The type of LayerNorm variant to use. Default: “LayerNorm”.
        # If a string, must be one of “LayerNormNoBias”, “LayerNorm”,
        # “TimeBatchNorm2d”. Otherwise, must be a custom nn.Module.
        self.norm_type = 'LayerNorm'
        self.normalize_before = False
        self.use_static_covariates = False
        # Whether to use reversible instance normalization RINorm
        # against distribution shift as shown in [3]_.
        # It is only applied to the features of the target series and not the covariates.
        self.use_reversible_instance_norm = True
        self.optimizer_kwargs = self.get_optimizer_kwargs()
        self.pl_trainer_kwargs = self.get_pl_trainer_kwargs(full_training)
        self.lr_scheduler_cls = torch.optim.lr_scheduler.ExponentialLR
        self.lr_scheduler_kwargs = {"gamma": 0.999}
        self.likelihood = None  # use a `likelihood` for probabilistic forecasts
        self.loss_fn = MSELoss()  # use a `loss_fn` for determinsitic model
        self.save_checkpoints = True  # checkpoint to retrieve the best performing model state,
        # 是否覆盖同名的模型的checkpoints.
        self.force_reset = True

    def get_pl_trainer_kwargs(self, full_training):
        # early stopping: this setting stops training once the validation
        # loss has not decreased by more than 1e-5 for 10 epochs
        early_stopper = EarlyStopping(
            monitor="val_loss",
            patience=10,
            min_delta=1e-6,
            # min_delta=5,
            mode="min",
        )

        # PyTorch Lightning Trainer arguments (you can add any custom callback)
        if full_training:
            limit_train_batches = None
            limit_val_batches = None
            max_epochs = 500
            batch_size = 256
        else:
            limit_train_batches = 20
            limit_val_batches = 10
            max_epochs = 40
            batch_size = 64

        # only show the training and prediction progress bars
        progress_bar = TFMProgressBar(
            enable_sanity_check_bar=False, enable_validation_bar=False
        )

        pl_trainer_kwargs = {
            "gradient_clip_val": 1,  # 梯度剪裁
            "max_epochs": max_epochs,
            "limit_train_batches": limit_train_batches,
            "limit_val_batches": limit_val_batches,
            "accelerator": "auto",
            "callbacks": [early_stopper, progress_bar],
        }

        return pl_trainer_kwargs

    def get_optimizer_kwargs(self):
        # optimizer setup, uses Adam by default
        optimizer_kwargs = {
            "lr": 1e-4,
            # "optimizer_cls": torch.optim.Adam
        }
        return optimizer_kwargs