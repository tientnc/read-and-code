import os

import qlib

provider_uri = os.getenv("QLIB_PROVIDER_URI", "~/.qlib/qlib_data/cn_data")
market = os.getenv("QLIB_MARKET")
start_time = os.getenv("QLIB_DATA_START_TIME", "2015-01-01")

qlib.init(provider_uri=provider_uri)
# qlib.init(provider_uri="~/.qlib/qlib_data/us_data")
from qlib.data import D

instruments = D.instruments(market) if market else D.instruments()
fields = ["$open", "$close", "$high", "$low", "$volume"]  # , "$amount", "$turn", "$pettm", "$pbmrq"
data = D.features(instruments, fields, freq="day").swaplevel().sort_index().loc[start_time:].sort_index()

# Calculate returns per instrument
data["$return"] = data.groupby(level="instrument")["$close"].pct_change(fill_method=None).fillna(0)

print(data)

data.to_hdf("./daily_pv_all.h5", key="data")

fields = ["$open", "$close", "$high", "$low", "$volume"]  # , "$amount", "$turn", "$pettm", "$pbmrq"
data = (
    D.features(instruments, fields, freq="day")
    .swaplevel()
    .sort_index()
    .loc[start_time:]
    .swaplevel()
    .loc[data.reset_index()["instrument"].unique()[:100]]
    .swaplevel()
    .sort_index()
)

# Calculate returns per instrument
data["$return"] = data.groupby(level="instrument")["$close"].pct_change(fill_method=None).fillna(0)
print(data)
data.to_hdf("./daily_pv_debug.h5", key="data")
