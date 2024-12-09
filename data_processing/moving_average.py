import numpy as np
import bottleneck as bn

def moving_average(arr,window):
    window = np.round(window).astype(int)
    half_window = np.ceil(window/2).astype(int)

    if not isinstance(arr, np.ndarray):
        arr = arr.to_numpy()

    arr_moving_avg = bn.move_mean(arr, window=half_window, min_count=1)
    arr_moving_avg = np.flip(bn.move_mean(np.flip(arr_moving_avg) , window=half_window, min_count=1))
    return arr_moving_avg