import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import time
from tqdm import tqdm
from pathlib import Path
from dateutil.relativedelta import relativedelta
import numpy as np

def get_all_stocks_in_period(start_date, end_date):
    """Get all stock codes that appeared in the specified period"""
    all_stocks = set()
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    current = start
    while current <= end:
        query_date = current.strftime('%Y-%m-%d')
        stock_rs = bs.query_all_stock(query_date)
        stock_df = stock_rs.get_data()
        if not stock_df.empty:
            all_stocks.update(stock_df['code'].tolist())
        current += relativedelta(years=1)
        if current > end:
            break
    print(f"Fetched {len(all_stocks)} stocks")
    return all_stocks

def download_stock_data(start_date, end_date, output_dir):
    """Download or update stock data to the latest date"""
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f'Login failed: {lg.error_msg}')
        return
    
    try:
        all_stocks = get_all_stocks_in_period(start_date, end_date)
        fields = "date,code,open,high,low,close,preclose,volume,amount,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def download_single_stock(code):
            code_clean = code.replace('.', '')
            output_file = output_path / f"{code_clean}.csv"
            
            # Determine the download start date for this stock
            if output_file.exists():
                existing_df = pd.read_csv(output_file)
                if not existing_df.empty:
                    existing_df['date'] = pd.to_datetime(existing_df['date'])
                    last_date = existing_df['date'].max()
                    code_download_start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
                    # Skip if no update is needed
                    # print(f"Stock {code} downloaded start date: {code_download_start_date}, end date: {last_date.strftime('%Y-%m-%d' )}")
                    if code_download_start_date == end_date:
                        print(f"Stock {code} does not need an update")
                        return
                else:
                    code_download_start_date = start_date
            else:
                code_download_start_date = start_date
            
            # Download incremental data
            print(f"Downloading {code} data... date range: {code_download_start_date} to {end_date}")
            rs = bs.query_history_k_data_plus(
                code,
                fields,
                start_date=code_download_start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="1" # adjusted close
            )
            
            if rs.error_code != '0':
                print(f"Failed to fetch {code} data: {rs.error_msg}")
                return
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())



            # Get adjustment factors
            rs_list = []
            rs_adj = bs.query_adjust_factor(
                code,
                start_date=code_download_start_date,
                end_date=end_date,
            )

            while (rs_adj.error_code == '0') & rs_adj.next():
                rs_list.append(rs_adj.get_row_data())

            adj_df = pd.DataFrame(rs_list, columns=rs_adj.fields).set_index('dividOperateDate')['adjustFactor']
            adj_df = adj_df.rename('factor')

            
            if data_list:
                new_df = pd.DataFrame(data_list, columns=rs.fields).set_index('date')
                new_df = pd.concat([new_df, adj_df], axis=1).ffill().fillna(1)
                
                new_df['code'] = new_df['code'].str.replace('.', '', regex=False)
                # new_df['factor'] = np.ones(len(new_df))
                numeric_cols = new_df.columns[2:]
                new_df[numeric_cols] = new_df[numeric_cols].apply(pd.to_numeric, errors='coerce')

                new_df = new_df.reset_index()
                new_df = new_df.rename(columns={'index': 'date'})
                
                # Merge and save data
                if output_file.exists():
                    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['date', 'code'])
                    combined_df['date'] = pd.to_datetime(combined_df['date'])
                    combined_df = combined_df.sort_values('date')
                else:
                    combined_df = new_df
                
                
                combined_df.to_csv(output_file, index=False, encoding='utf-8')
            
            # time.sleep(0.5)
        
        # # Use a thread pool for concurrent downloads
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(download_single_stock, code) for code in all_stocks]
            
            # Use tqdm to show progress
            for _ in tqdm(as_completed(futures), total=len(futures), desc="Download progress"):
                pass

        # for code in all_stocks:
        #     download_single_stock(code)
                
    finally:
        bs.logout()



def download_oneday_stock_data_(date):

    #### Log in ####
    lg = bs.login()
    # Show login response information
    print('login respond error_code:'+lg.error_code)
    print('login respond  error_msg:'+lg.error_msg)

    #### Get all security information for a date ####
    rs = bs.query_all_stock(day=date)
    print('query_all_stock respond error_code:'+rs.error_code)
    print('query_all_stock respond  error_msg:'+rs.error_msg)

    #### Print the result set ####
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # Get one record and merge it into the result
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)

    #### Output the result set to a CSV file ####   
    # result.to_csv("D:\\all_stock.csv", encoding="gbk", index=False)
    print(result)

    #### Log out ####
    bs.logout()

if __name__ == '__main__':
    # Dynamically set the end date to the current date
    START_DATE = '2014-12-31'
    END_DATE = (datetime.now()).strftime('%Y-%m-%d') # '2025-01-01'  - timedelta(days=7)
    DATA_DIR = '~/.qlib/qlib_data/cn_data/raw_data_back_adjust'
    
    print("Starting stock data download... date range:", START_DATE, "to", END_DATE)
    download_stock_data(START_DATE, END_DATE, DATA_DIR)
    # download_oneday_stock_data_((datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d'))
    print("Download completed!")