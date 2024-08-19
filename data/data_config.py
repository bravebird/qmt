from pathlib2 import Path

# config = {
#     'work_path': Path('.'),
#     'data_path': Path("assets/data"),
#     'data_save_paths': {
#         'train': "combined_train.pkl",
#         'val': "combined_val.pkl",
#         'test': "combined_test.pkl",
#         'past_cov': "combined_past_cov.pkl",
#         'future_cov': "future_cov.pkl",
#         'scaler_train': 'combine_scaler_train.pkl',
#         'scaler_past': 'combine_scaler_past.pkl'
#     },
#     'set_length': {
#         'val_length': 60,
#         'test_length': 60,
#         'header_length': 30
#     }
# }

config = {
    'work_path': Path('.'),
    'data_path': Path("assets/data"),
    'data_save_paths': {
        'train': "combined_train.pkl",
        'val': "combined_val.pkl",
        'test': "combined_test.pkl",
        'past_cov': "combined_past_cov.pkl",
        'future_cov': "future_cov.pkl",
        'scaler_train': 'combine_scaler_train.pkl',
        'scaler_past': 'combine_scaler_past.pkl'
    },
    'data_list_paths': {
        'train': "list_train.pkl",
        'val': "list_val.pkl",
        'test': "list_test.pkl",
        'past_cov': "list_past_cov.pkl",
        'future_cov': "list_future_cov.pkl",
        'scaler_train': 'list_scaler_train.pkl',
        'scaler_past': 'list_scaler_past.pkl'
    },
    'set_length': {
        'val_length': 60,
        'test_length': 60,
        'header_length': 0
    }
}