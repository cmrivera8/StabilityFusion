import pandas as pd

def resample_data(time, values, interval='1s'):
    """
    Resample data based on time and values arrays, applying a moving average.

    Parameters:
        time (array-like): Array of timestamps (e.g., seconds).
        values (array-like): Array of corresponding values.
        interval (str): Resampling interval (default is '1s' for 1 second).

    Returns:
        pd.DataFrame: Resampled data with columns ['time', 'values'].
    """
    # Convert time array to DatetimeIndex (assuming time is in seconds since epoch)
    time_index = pd.to_datetime(time, unit='s')

    # Create a DataFrame with time as index
    data = pd.DataFrame({'values': values}, index=time_index)

    # Resample the data and compute the mean
    resampled_data = data['values'].resample(interval).mean()

    # Handle Nan values
    resampled_data = resampled_data.ffill()

    # Reset index to get timestamps back as a column
    resampled_data = resampled_data.reset_index()

    # Rename columns for clarity
    resampled_data.columns = ['time', 'values']

    # Convert the time column to Unix timestamps using .dt.timestamp()
    resampled_data['time'] = resampled_data['time'].astype('int64') / 10**9

    return resampled_data["time"].to_numpy(), resampled_data["values"].to_numpy()