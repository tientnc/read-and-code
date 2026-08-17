import numpy as np
import pandas as pd
from joblib import Parallel, delayed


def datatype_adapter(func):
    def wrapper(*args):
        # For a single input, convert a NumPy array to a DataFrame
        if len(args) == 1 and isinstance(args[0], np.ndarray):
            # Convert a NumPy array to a DataFrame
            new_args = (pd.DataFrame(args[0]),)
            # Execute the function and convert back to a NumPy array
            result = func(*new_args)
            return result
        # For a single float input, convert to a DataFrame and then back to a float
        if len(args) == 1 and isinstance(args[0], (float, int)):
            new_args = (pd.DataFrame([args[0]]),)
            result = func(*new_args)
            return float(result.iloc[0])
        # For typical inputs, func(df, p) or func(df)
        if (len(args) == 2 and isinstance(args[0], np.ndarray) and not isinstance(args[1], np.ndarray)):
            # Convert a NumPy array to a DataFrame
            new_args = (pd.DataFrame(args[0]), args[1])
            # Execute the function and convert back to a NumPy array
            result = func(*new_args)
        elif (len(args) == 2 and isinstance(args[1], np.ndarray) and not isinstance(args[0], np.ndarray)):
            # Convert a NumPy array to a DataFrame
            new_args = (args[0], pd.DataFrame(args[1]))
            # Execute the function and convert back to a NumPy array
            result = func(*new_args)
        else:
            result = func(*args)
        return result

    return wrapper

@datatype_adapter
def DELTA(df:pd.DataFrame, p:int=1):
    return df.groupby('instrument').transform(lambda x: x.diff(periods=p))

@datatype_adapter
def RANK(df:pd.DataFrame):
    """Calculate cross-sectional rank"""
    return df.groupby('datetime').rank(pct=True)

@datatype_adapter
def MEAN(df:pd.DataFrame):
    """Calculate cross-sectional mean"""
    return df.groupby('datetime').mean()

@datatype_adapter
def STD(df:pd.DataFrame):
    """Calculate cross-sectional standard deviation"""
    return df.groupby('datetime').std()

@datatype_adapter
def SKEW(df:pd.DataFrame):
    """Calculate cross-sectional skewness"""
    return df.groupby('datetime').skew()

@datatype_adapter
def KURT(df:pd.DataFrame):
    """Calculate cross-sectional kurtosis"""
    return df.groupby('datetime').kurt()

@datatype_adapter
def MAX(df:pd.DataFrame):
    """Calculate cross-sectional maximum"""
    return df.groupby('datetime').max()

@datatype_adapter
def MIN(df:pd.DataFrame):
    """Calculate cross-sectional minimum"""
    return df.groupby('datetime').min()

@datatype_adapter
def MEDIAN(df:pd.DataFrame):
    """Calculate cross-sectional median"""
    return df.groupby('datetime').median()


@datatype_adapter
def TS_RANK(df:pd.DataFrame, p:int=5):
    """Calculate time-series percentile rank"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).rank(pct=True))

@datatype_adapter
def TS_MAX(df:pd.DataFrame, p:int=5):
    """Calculate the time-series maximum"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).max())

@datatype_adapter
def TS_MIN(df:pd.DataFrame, p:int=5):
    """Calculate the time-series minimum"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).min())

@datatype_adapter
def TS_MEAN(df:pd.DataFrame, p:int=5):
    """Calculate the time-series mean"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).mean())

@datatype_adapter
def TS_MEDIAN(df:pd.DataFrame, p:int=5):
    """Calculate the time-series median"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).median())

@datatype_adapter
def PERCENTILE(df: pd.DataFrame, q: float, p: int = None):
    """
    Calculate quantiles for the given data.

    Args:
        df (pd.DataFrame): Input data, which can be a DataFrame or NumPy array.
        q (float): Quantile in the range [0, 1].
        p (int): Rolling window size; if provided, calculate rolling quantiles.

    Returns:
        pd.DataFrame: DataFrame containing quantiles.
    """
    assert 0 <= q <= 1, "Quantile q must be in [0, 1]"
    
    if p is not None:
        # If a rolling window size is provided, calculate rolling quantiles
        return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).quantile(q))
    else:
        # If no rolling window size is provided, calculate quantiles directly
        return df.groupby('instrument').transform(lambda x: x.quantile(q))



@datatype_adapter
def TS_SUM(df:pd.DataFrame, p:int=5):
    """Calculate the cumulative sum of a time series"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).sum())


@datatype_adapter
def TS_ARGMAX(df: pd.DataFrame, p: int = 5):
    """Calculate days since the maximum value occurred in the past p days"""
    def rolling_argmax(window):
        return len(window) - window.argmax() - 1
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(rolling_argmax, raw=True))

@datatype_adapter
def TS_ARGMIN(df: pd.DataFrame, p: int = 5):
    """Calculate days since the minimum value occurred in the past p days"""
    def rolling_argmin(window):
        return len(window) - window.argmin() - 1
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(rolling_argmin, raw=True))



def MAX(x:pd.DataFrame, y:pd.DataFrame, z:pd.DataFrame=None):
    """Calculate the maximum across multiple DataFrames"""
    if z is None:
        return np.maximum(x, y)
    else:
        return np.maximum(np.maximum(x, y), z)




def MIN(x:pd.DataFrame, y:pd.DataFrame, z:pd.DataFrame=None):
    """Calculate the minimum across multiple DataFrames""" 
    if z is None:
        return np.minimum(x, y)
    else:
        return np.minimum(np.minimum(x, y), z)
    


@datatype_adapter
def ABS(df:pd.DataFrame):
    """Calculate the absolute value of each DataFrame element"""   
    return df.groupby('instrument').transform(lambda x: x.abs())    

@datatype_adapter
def DELAY(df:pd.DataFrame, p:int=1):
    """Delay data by p periods"""
    assert p >= 0, ValueError("DELAY duration cannot be less than 0; otherwise it would cause look-ahead bias")
    return df.groupby('instrument').transform(lambda x: x.shift(p))


def TS_CORR(df1:pd.Series, df2: np.ndarray | pd.Series, p:int=5):
    """Calculate rolling correlation between two series"""
    if isinstance(df2, np.ndarray) and p != len(df2):
        p = len(df2)
        def corr(window):
            x = window
            y = df2[:len(window)]
            # Calculate means
            mean_x = np.mean(x)
            mean_y = np.mean(y)
            
            # Calculate covariance and standard deviation
            cov = np.sum((x - mean_x) * (y - mean_y))
            std_x = np.sqrt(np.sum((x - mean_x) ** 2))
            std_y = np.sqrt(np.sum((y - mean_y) ** 2))
            
            # Calculate correlation coefficients
            return cov / (std_x * std_y)
        
        return df1.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=2).apply(corr, raw=True))
    else:
        def rolling_corr(group, df2, p):
            # Get the instrument of the current group
            instrument = group.name
            # Extract the matching instrument data from df2
            df2_group = df2.xs(instrument, level='instrument')
            # Calculate rolling correlation
            return group.rolling(p, min_periods=2).corr(df2_group)

        # Use groupby and apply to calculate rolling correlation for each instrument
        result = df1.groupby('instrument').apply(lambda x: rolling_corr(x, df2, p))
        # Because apply changes the index structure, restore the original structure
        result = result.reset_index(level=0, drop=True).sort_index()
        return result


def TS_COVARIANCE(df1:pd.DataFrame, df2:pd.DataFrame, p:int=5):  
    """Calculate rolling covariance between two series"""
    if isinstance(df2, np.ndarray) and p != len(df2):
        p = len(df2)
        def cov(window):
            return np.cov(window, df2[:len(window)])
        return df1.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=2).apply(cov, raw=True))
    else:
        def rolling_cov(group, df2, p):
            # Get the instrument of the current group
            instrument = group.name
            # Extract the matching instrument data from df2
            df2_group = df2.xs(instrument, level='instrument')
            # Calculate rolling correlation
            return group.rolling(p, min_periods=2).cov(df2_group)

        # Use groupby and apply to calculate rolling correlation for each instrument
        result = df1.groupby('instrument').apply(lambda x: rolling_cov(x, df2, p))
        # Because apply changes the index structure, restore the original structure
        result = result.reset_index(level=0, drop=True).sort_index()
        return result

@datatype_adapter
def TS_STD(df:pd.DataFrame, p:int=20):
    """Calculate time-series rolling standard deviation"""
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).std())





@datatype_adapter
def TS_VAR(df: pd.DataFrame, p: int = 5, ddof: int = 1):
    """Calculate time-series rolling variance"""
    return df.groupby('instrument').transform(
        lambda x: x.rolling(p, min_periods=1).var(ddof=ddof)
    )

@datatype_adapter
def SIGN(df: pd.DataFrame):
    """Calculate the sign of each DataFrame element"""
    return np.sign(df)

@datatype_adapter
def SMA(df:pd.DataFrame, m:float=None, n:float=None):
    """
    Calculate the simple moving average (SMA)
    
    Args:
        df (pd.DataFrame): Input data
        m (float, optional): Moving-average period
        n (float, optional): Moving-average weight
    Y_{i+1} = m/n*X_i + (1 - m/n)*Y_i
    """
        
    if isinstance(m, int) and m >= 1 and n is None:
        return df.groupby('instrument').transform(lambda x: x.rolling(m, min_periods=1).mean())
    else:
        return df.groupby('instrument').transform(lambda x: x.ewm(alpha=n/m).mean())

@datatype_adapter
def EMA(df:pd.DataFrame, p):
    """
    Calculate the exponential moving average (EMA)
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Moving-average period

    Returns:
        pd.DataFrame: Exponential moving-average result
    """
    return df.groupby('instrument').transform(lambda x: x.ewm(span=int(p), min_periods=1).mean())
    
@datatype_adapter
def WMA(df:pd.DataFrame, p:int=20):
    """
    Calculate the weighted moving average (WMA)
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Moving-average period
        
    Returns:
        pd.DataFrame: Weighted moving-average result
    """
    # Calculate weights; the most recent data (i=0) has the largest weight
    weights = [0.9**i for i in range(p)][::-1]
    def calculate_wma(window):
        return (window * weights[:len(window)]).sum() / sum(weights[:len(window)])

    # Apply weights to calculate rolling WMA
    return df.groupby('instrument').transform(lambda x: x.rolling(window=p, min_periods=1).apply(calculate_wma, raw=True))

@datatype_adapter
def COUNT(cond:pd.DataFrame, p:int=20):
    """
    Calculate conditional counts
    
    Args:
        cond (pd.DataFrame): Condition data
        p (int): Rolling window size
    
    Returns:
        pd.DataFrame: Conditional count result
    """
    return cond.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).sum())

@datatype_adapter
def SUMIF(df:pd.DataFrame, p:int, cond:pd.DataFrame):
    """
    Calculate the rolling sum of a series where the condition is met
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Rolling window size
        cond (pd.DataFrame): Condition data
    
    Returns:
        pd.DataFrame: Rolling sum of the series where the condition is met
    """
    return (df * cond).groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).sum())

@datatype_adapter
def FILTER(df:pd.DataFrame, cond:pd.DataFrame):
    """
    Filter a series by condition, keeping elements that satisfy it and setting others to 0
    
    Args:
        df (pd.DataFrame): Input data
        cond (pd.DataFrame): Condition data
    
    Returns:
        pd.DataFrame: Series filtered by condition
    """
    return df.mul(cond)
    

@datatype_adapter
def PROD(df:pd.DataFrame, p:int=5):
    """
    Calculate the rolling product of a series
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Rolling window size
    
    Returns:
        pd.DataFrame: Rolling product result
    """

    # Use rolling to create a sliding window, then apply cumulative multiplication
    if isinstance(p, int):
        return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(lambda x: x.prod(), raw=True))
    else:
        return df.mul(p)    

@datatype_adapter
def DECAYLINEAR(df:pd.DataFrame, p:int=5):
    """
    Calculate the linear-decay weighted average of a series
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Rolling window size
    
    Returns:
        pd.DataFrame: Linear-decay weighted-average result
    """
    assert isinstance(p, int), ValueError(f"DECAYLINEAR only accepts a positive integer parameter n; received {type(p).__name__}")
    decay_weights = np.arange(1, p+1, 1)
    decay_weights = decay_weights / decay_weights.sum()
    
    def calculate_deycaylinear(window):
        return (window * decay_weights[:len(window)]).sum()
    
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(calculate_deycaylinear, raw=True))

@datatype_adapter
def HIGHDAY(df:pd.DataFrame, p:int=5):
    """
    Calculate days since the maximum value occurred in the series
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Rolling window size
    
    Returns:
        pd.DataFrame: Days since the maximum value occurred
    """
    assert isinstance(p, int), ValueError(f"HIGHDAY only accepts a positive integer parameter n; received {type(p).__name__}")
    def highday(window):
        return len(window) - window.argmax(axis=0)
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(highday, raw=True))

@datatype_adapter
def LOWDAY(df:pd.DataFrame, p:int=5):
    """
    Calculate days since the minimum value occurred in the series
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Rolling window size
    
    Returns:
        pd.DataFrame: Days since the minimum value occurred
    """
    assert isinstance(p, int), ValueError(f"LOWDAY only accepts a positive integer parameter n; received {type(p).__name__}")
    def lowday(window):
        return len(window) - window.argmin(axis=0)
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).apply(lowday, raw=True))
    

def SEQUENCE(n):
    """
    Generate an arithmetic sequence from 1 to n
    
    Args:
        n (int): Sequence length
    """
    assert isinstance(n, int), ValueError(f"SEQUENCE(n) only accepts a positive integer parameter n; received {type(n).__name__}")
    return np.linspace(1, n, n, dtype=np.float32)

@datatype_adapter
def SUMAC(df:pd.DataFrame, p:int=10):
    """
    Calculate the rolling cumulative sum of a series
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Rolling window size
    
    Returns:
        pd.DataFrame: Rolling cumulative-sum result
    """
    assert isinstance(p, int), ValueError(f"SUMAC only accepts a positive integer parameter n; received {type(p).__name__}")
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).sum())



def calculate_beta(y, x):
    """Calculate the regression coefficient (beta)"""
    X = np.vstack([x, np.ones(len(x))]).T
    beta, _ = np.linalg.lstsq(X, y, rcond=None)[0]
    return beta

def rolling_beta(df1_group, df2_group, p):
    """Calculate beta over rolling windows of df1 and df2"""
    result = np.empty(len(df1_group))
    result[:] = np.nan  # Initialize the result as NaN

    # Calculate beta over rolling windows
    for i in range(p - 1, len(df1_group)):
        window_y = df1_group.iloc[i - p + 1 : i + 1].values
        window_x = df2_group.iloc[:p].values if df1_group.shape != df2_group.shape else df2_group.iloc[i - p + 1 : i + 1].values
        result[i] = calculate_beta(window_y, window_x)

    # Return a Series aligned to the input data index
    return pd.Series(result, index=df1_group.index)


def REGBETA(df1: pd.DataFrame, df2: pd.DataFrame, p: int = 5, n_jobs: int = -1):
    """
    Calculate rolling regression coefficient (beta) for df1 and df2
    
    Args:
        df1 (pd.DataFrame): First DataFrame containing the target variable.
        df2 (pd.DataFrame): Second DataFrame containing the explanatory variable.
        p (int): Rolling window size.
        n_jobs (int): Number of CPU cores for parallel computation.
    
    Returns:
        pd.Series: Rolling regression coefficient result.
    """
    assert not (isinstance(df2, np.ndarray) and isinstance(df1, np.ndarray)), "df1 and df2 cannot both be np.ndarray; at least one must be a DataFrame, such as ."
    if isinstance(df2, np.ndarray) or isinstance(df1, np.ndarray):
        if isinstance(df1, np.ndarray):
            df3 = df1
            df1 = df2
            df2 = df3
            p = min(len(df2), p)
            df2 = pd.Series(df2)
        # Fill missing values
        df1 = df1.fillna(0)
        
        # Get grouped data
        df1_groups = list(df1.groupby('instrument'))
        df2 = pd.Series(df2[:p])
        
        # Use joblib for parallel computation
        results = Parallel(n_jobs=n_jobs)(
            delayed(rolling_beta)(df1_group, df2, p)
            for _, df1_group in df1_groups
        )
        
        # Merge results into a Series and ensure the index is aligned
        result = pd.concat(results)
        result = result.sort_index()  # Sort by index
        return result
    
    else:
        # Ensure df1 and df2 indexes are aligned
        assert df1.index.equals(df2.index), "df1 and df2 indexes must be aligned"
        
        # Fill missing values
        df1 = df1.fillna(0)
        df2 = df2.fillna(0)
        
        # Get grouped data
        df1_groups = list(df1.groupby('instrument'))
        df2_groups = list(df2.groupby('instrument'))
        
        # Ensure group order is consistent
        if len(df1_groups) != len(df2_groups):
            raise ValueError("The number of groups in df1 and df2 is inconsistent; please check the data.")
        
        # Use joblib for parallel computation
        results = Parallel(n_jobs=n_jobs)(
            delayed(rolling_beta)(df1_group, df2_group, p)
            for (_, df1_group), (_, df2_group) in zip(df1_groups, df2_groups)
        )
        
        # Merge results into a Series and ensure the index is aligned
        result = pd.concat(results)
        result = result.sort_index()  # Sort by index
        return result



def calculate_residuals(y, x):
    """Calculate residuals (actual values - predicted values)"""
    # Add a constant term to calculate the intercept
    X = np.vstack([x, np.ones(len(x))]).T
    # Use least squares to calculate regression coefficients
    beta, intercept = np.linalg.lstsq(X, y, rcond=None)[0]
    # Calculate predicted values
    y_pred = beta * x + intercept
    # Calculate residuals (actual values - predicted values)
    residuals = y - y_pred
    return residuals[-1]  # Return the latest residual value in the rolling window

def rolling_residuals(df1_group, df2_group, p):
    """Calculate residuals over rolling windows of df1 and df2"""
    result = np.empty(len(df1_group))
    result[:] = np.nan  # Initialize the result as NaN

    # Calculate residuals over rolling windows
    for i in range(p - 1, len(df1_group)):
        window_y = df1_group.iloc[i - p + 1 : i + 1].values
        window_x = df2_group.iloc[:p].values if df1_group.shape != df2_group.shape else df2_group.iloc[i - p + 1 : i + 1].values
        result[i] = calculate_residuals(window_y, window_x)

    # Return a Series aligned to the input data index
    return pd.Series(result, index=df1_group.index)


def REGRESI(df1: pd.DataFrame, df2: pd.DataFrame, p: int = 5, n_jobs: int = -1):
    """
    Calculate rolling residuals for df1 and df2
    
    Args:
        df1 (pd.DataFrame): First DataFrame containing the target variable.
        df2 (pd.DataFrame): Second DataFrame containing the explanatory variable.
        p (int): Rolling window size.
        n_jobs (int): Number of CPU cores for parallel computation.
    
    Returns:
        pd.Series: Rolling residual result.
    """
    
    assert not (isinstance(df2, np.ndarray) and isinstance(df1, np.ndarray)), "df1 and df2 cannot both be np.ndarray; at least one must be a DataFrame, such as ."
    if isinstance(df2, np.ndarray) or isinstance(df1, np.ndarray):
        if isinstance(df1, np.ndarray):
            df3 = df1
            df1 = df2
            df2 = df3
            p = min(len(df2), p)
        # Fill missing values
        df1 = df1.fillna(0)
        df2 = pd.Series(df2[:p])
        
        # Get grouped data
        df1_groups = list(df1.groupby('instrument'))
        
        # Use joblib for parallel computation
        results = Parallel(n_jobs=n_jobs)(
            delayed(rolling_residuals)(df1_group, df2, p)
            for _, df1_group in df1_groups
        )
        
        # Merge results into a Series and ensure the index is aligned
        result = pd.concat(results)
        result = result.sort_index()  # Sort by index
        return result
    
    else:
        # Ensure df1 and df2 indexes are aligned
        assert df1.index.equals(df2.index), "df1 and df2 indexes must be aligned"
        
        # Fill missing values
        df1 = df1.fillna(0)
        df2 = df2.fillna(0)
        
        # Get grouped data
        df1_groups = list(df1.groupby('instrument'))
        df2_groups = list(df2.groupby('instrument'))
        
        # Ensure group order is consistent
        if len(df1_groups) != len(df2_groups):
            raise ValueError("The number of groups in df1 and df2 is inconsistent; please check the data.")
        
        # Use joblib for parallel computation
        results = Parallel(n_jobs=n_jobs)(
            delayed(rolling_residuals)(df1_group, df2_group, p)
            for (_, df1_group), (_, df2_group) in zip(df1_groups, df2_groups)
        )
        
        # Merge results into a Series and ensure the index is aligned
        result = pd.concat(results)
        result = result.sort_index()  # Sort by index
        return result

        
### Math operations
@datatype_adapter
def EXP(df:pd.DataFrame):
    """
    Calculate the exponential value of a series
    
    Args:
        df (pd.DataFrame): Input data
        
    Returns:
        pd.DataFrame: Exponential result
    """
    return df.apply(np.exp)

@datatype_adapter
def SQRT(df: pd.DataFrame):
    """Calculate the square root of a series"""
    if isinstance(df, int):
        return np.sqrt(df)
    return df.apply(np.sqrt)

@datatype_adapter
def LOG(df:pd.DataFrame):
    """Calculate the natural logarithm of a series"""
    if isinstance(df, int):
        return np.log(df)
    return (df+1).apply(np.log)

@datatype_adapter
def INV(df: pd.DataFrame):
    """Calculate the reciprocal of a series (1/x)"""
    return 1 / df

@datatype_adapter
def POW(df:pd.DataFrame, n:int):
    """Calculate the power of a series"""
    return np.power(df, n)

def FLOOR(df:pd.DataFrame):
    """Calculate the floor of a series"""
    return df.apply(np.floor)

@datatype_adapter
def TS_ZSCORE(df: pd.DataFrame, p:int=5):
    assert isinstance(p, int), ValueError(f"TS_ZSCORE only accepts a positive integer parameter n; received {type(p).__name__}")
    # assert isinstance(df, pd.DataFrame), ValueError(f"TS_ZSCORE only accepts pd.DataFrame as the type of A; received {type(df).__name__}")
    return (df - df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).mean())) / df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).std())

@datatype_adapter
def ZSCORE(df):
    # Calculate mean and standard deviation for each factor cross-section
    mean = df.groupby('datetime').mean()
    std = df.groupby('datetime').std()
    
    # Calculate z-score: (X - μ) / σ
    zscore = (df - mean) / std
    return zscore

@datatype_adapter
def SCALE(df: pd.DataFrame, target_sum: float = 1.0):
    """
    Normalize a series so the sum of absolute values equals target_sum
    """
    # Calculate the current sum of absolute values
    abs_sum = ABS(df).groupby('datetime').sum()
    # Scale the values
    return df.multiply(target_sum).div(abs_sum, axis=0)


@datatype_adapter
def TS_MAD(df: pd.DataFrame, p: int = 5):
    """
    Calculate the rolling median absolute deviation (MAD) of a time series
    
    MAD = median(|X_i - median(X)|)
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Rolling window size
        
    Returns:
        pd.DataFrame: Rolling MAD result
    """
    def rolling_mad(window):
        # Calculate the median within the window
        median_val = np.median(window)
        # Calculate each value's absolute deviation from the median
        abs_dev = np.abs(window - median_val)
        # Return the median of these deviations
        return np.median(abs_dev)
    
    return df.groupby('instrument').transform(
        lambda x: x.rolling(p, min_periods=1).apply(rolling_mad, raw=True)
    )


@datatype_adapter
def TS_QUANTILE(df: pd.DataFrame, p: int = 5, q: float = 0.5):
    """
    Calculate rolling quantiles of a time series
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Rolling window size
        q (float): Quantile in the range [0, 1]
        
    Returns:
        pd.DataFrame: Rolling quantile result
    """
    assert 0 <= q <= 1, "Quantile q must be in [0, 1]"
    return df.groupby('instrument').transform(lambda x: x.rolling(p, min_periods=1).quantile(q))

@datatype_adapter
def TS_PCTCHANGE(df: pd.DataFrame, p: int = 1):
    """
    Calculate time-series percentage change
    
    Args:
        df (pd.DataFrame): Input data
        p (int): Calculation interval; defaults to 1 (adjacent periods)
        
    Returns:
        pd.DataFrame: Percentage-change result
    """
    return df.groupby('instrument').transform(lambda x: x.pct_change(periods=p).fillna(0))


def ADD(df1, df2):
    return np.add(df1, df2)
        
        
def SUBTRACT(df1, df2):
    return np.subtract(df1, df2)
    
def MULTIPLY(df1, df2):
    return np.multiply(df1, df2)
    
def DIVIDE(df1, df2):
    return np.divide(df1, df2)
    
def AND(df1, df2):
    return np.bitwise_and(df1.astype(np.bool_), df2.astype(np.bool_))

def OR(df1, df2):
    return np.bitwise_or(df1.astype(np.bool_), df2.astype(np.bool_))



def MACD(price_df, short_window=12, long_window=26):
    """
    Calculate the MACD indicator
    
    Args:
        price_df: pd.DataFrame - Price data
        short_window: int - Short-term EMA window size, default 12
        long_window: int - Long-term EMA window size, default 26
        
    Returns:
        pd.DataFrame: MACD result
    """
    # Calculate short-term EMA
    short_ema = EMA(price_df, short_window)
    
    # Calculate long-term EMA
    long_ema = EMA(price_df, long_window)
    
    # Calculate the MACD difference
    macd = short_ema - long_ema
    return macd


def RSI(price_df, window=14):
    """
    Calculate the relative strength index (RSI)
    
    Args:
        price_df: pd.DataFrame - Price data
        window: int - RSI window size, default 14

    Returns:
        pd.DataFrame: RSI result
    """
    # Calculate price changes
    price_change = DELTA(price_df, 1)
    
    # Calculate gains and losses separately using vectorized operations
    up = (price_change > 0) * price_change
    down = (price_change < 0) * ABS(price_change)
    
    # Calculate EMA
    avg_up = EMA(up, window)
    avg_down = EMA(down, window)
    
    # Calculate RSI
    rsi = 100 - (100 / (1 + (avg_up / avg_down)))
    return rsi




def _calculate_rolling_mean(group_data):
    """Calculate the dynamic moving average for a single group"""
    price_group, window_group, group_name = group_data
    result = pd.Series(index=price_group.index, dtype=float)
    
    for i in range(len(price_group)):
        curr_window = int(window_group.iloc[i].values)
        if curr_window < 1:
            curr_window = 1
        if i < curr_window:
            result.iloc[i] = price_group.iloc[:i+1].mean()
        else:
            result.iloc[i] = price_group.iloc[i-curr_window+1:i+1].mean()
    
    return group_name, result

def _calculate_rolling_std(group_data):
    """Calculate the dynamic standard deviation for a single group"""
    price_group, window_group, group_name = group_data
    result = pd.Series(index=price_group.index, dtype=float)
    
    for i in range(len(price_group)):
        curr_window = int(window_group.iloc[i].values)
        if curr_window < 1:
            curr_window = 1
        if i < curr_window:
            result.iloc[i] = price_group.iloc[:i+1].std()
        else:
            result.iloc[i] = price_group.iloc[i-curr_window+1:i+1].std()
    
    return group_name, result



@datatype_adapter
def BB_MIDDLE(price_df, window, n_jobs=-1):
    """
    Calculate the Bollinger Band middle line; supports dynamic window sizes and parallel computation
    
    Args:
        price_df: pd.DataFrame - Price data
        window: int or pd.DataFrame - window size
        n_jobs: int - number of parallel jobs, default -1
    """
    if isinstance(window, (int, float)):
        # If window is fixed, use the original logic
        return price_df.groupby('instrument').transform(lambda x: x.rolling(int(window), min_periods=1).mean())
    else:
        window.index = price_df.index
        # Prepare data for parallel computation
        groups_data = [
            (price_group, 
             window.xs(group_name, level='instrument'), 
             group_name)
            for group_name, price_group in price_df.groupby('instrument')
        ]
        
        # Parallel computation
        results = Parallel(n_jobs=n_jobs)(
            delayed(_calculate_rolling_mean)(group_data)
            for group_data in groups_data
        )
        
        # Merge results
        final_result = pd.concat([result for _, result in sorted(results, key=lambda x: x[0])])
        return final_result

@datatype_adapter
def BB_UPPER(price_df, window, n_jobs=-1):
    """
    Calculate the Bollinger Band upper line; supports dynamic window sizes and parallel computation
    
    Args:
        price_df: pd.DataFrame - Price data
        window: int or pd.DataFrame - window size
        n_jobs: int - number of parallel jobs, default -1
    """
    
    if isinstance(window, (int, float)):
        # Standard-deviation calculation for a fixed window size
        middle_band = BB_MIDDLE(price_df, window, n_jobs)
        std = price_df.groupby('instrument').transform(lambda x: x.rolling(int(window), min_periods=1).std())
    else:
        window.index = price_df.index
        middle_band = BB_MIDDLE(price_df, window, n_jobs)
        # Prepare data for parallel computation
        groups_data = [
            (price_group, 
             window.xs(group_name, level='instrument'), 
             group_name)
            for group_name, price_group in price_df.groupby('instrument')
        ]
        
        # Calculate standard deviation in parallel
        results = Parallel(n_jobs=n_jobs)(
            delayed(_calculate_rolling_std)(group_data)
            for group_data in groups_data
        )
        
        # Merge results
        std = pd.concat([result for _, result in sorted(results, key=lambda x: x[0])])
    
    return middle_band + std

@datatype_adapter
def BB_LOWER(price_df, window, n_jobs=-1):
    """
    Calculate the Bollinger Band lower line; supports dynamic window sizes and parallel computation
    
    Args:
        price_df: pd.DataFrame - Price data
        window: int or pd.DataFrame - window size
        n_jobs: int - number of parallel jobs, default -1
    """
    
    if isinstance(window, (int, float)):
        # Standard-deviation calculation for a fixed window size
        middle_band = BB_MIDDLE(price_df, window, n_jobs)
        std = price_df.groupby('instrument').transform(lambda x: x.rolling(int(window), min_periods=1).std())
    else:
        window.index = price_df.index
        middle_band = BB_MIDDLE(price_df, window, n_jobs)
        # Prepare data for parallel computation
        groups_data = [
            (price_group, 
             window.xs(group_name, level='instrument'), 
             group_name)
            for group_name, price_group in price_df.groupby('instrument')
        ]
        
        # Calculate standard deviation in parallel
        results = Parallel(n_jobs=n_jobs)(
            delayed(_calculate_rolling_std)(group_data)
            for group_data in groups_data
        )
        
        # Merge results
        std = pd.concat([result for _, result in sorted(results, key=lambda x: x[0])])
    
    return middle_band - std
