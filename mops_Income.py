from os import replace
import requests as req
import re
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime
import pyodbc as odbc

# 年月(用今天去抓前一個月)
premonth = (datetime.date(datetime.date.today().year, datetime.date.today().month, 1) - datetime.timedelta(days = 1))
## ym要用list包起來
ym = [str( premonth.year - 1911 ) + "_" + str(premonth.month if premonth.month > 9 else str(premonth.month)[1:])]
# ym = ["108_1", "108_2", "108_3", "108_4", "108_5", "108_6", "108_7", "108_8", "108_9", "108_10", "108_11", "108_12"]
# yyyymm = datetime.date(premonth.year, premonth.month, 1)

# 股票類別(sii = 上市(listed company at stock exchange market), otc = 上櫃(listed company at over-the-counter market))
stockcatg = ["sii", "otc"]

head_info = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36"}


url_model = "https://mops.twse.com.tw/nas/t21/{}/t21sc03_{}_0.html"
# url_tmp = "https://mops.twse.com.tw/nas/t21/{}/t21sc03_" + str(ym) + "_0.html"
conn_sql = odbc.connect(Driver = '{SQL Server Native Client 11.0}', Server = "RAOICD01", database = "BIDC", user = "owner_sap", password = "sap@@20166")
cursor = conn_sql.cursor()

for catg in stockcatg:
    for period in ym:
        data_head = [] 
        data_item = []

        yyyymm = period.split("_")
        yyyymm = str(int(yyyymm[0]) + 1911) + "-" + str(yyyymm[1]) + "-1"

        url = url_model.format(catg, period)
        urlwithhead = req.get(url, headers = head_info)
        urlwithhead.encoding = "big5"
        
        #寫網頁原始碼到檔案中
        root =  bs(urlwithhead.text, "lxml")
        with open ("html_data/imcome_" + catg + ".html", mode = "w", encoding = "UTF-8") as web_html:
            web_html.write(root.prettify())
        #取半導體的table
        tb = root.find("th", text = re.compile(".*半導體")).find_parent("table")
        with open ("html_data/tb_semi_" + catg + ".html", mode = "w", encoding = "UTF-8") as web_html:
            web_html.write(tb.prettify())

        for head_line1 in tb.select("table > tr:nth-child(1) > th:nth-child(4)"):
            data_head.append("資料年月")
            for head_line2 in tb.select("table > tr:nth-child(2) > th"):
                # print(re.sub('<br\s*?>', ' ', head_line2.text))
                data_head.append(re.sub('<br\s*?>', ' ', head_line2.text))
            # print(head_line1.text)
            data_head.append(head_line1.text)
            data_head.append("上市/上櫃")
        # print(data_head)
        
        # 從第3個Row開始loop起(Row 3 以後是資料)
        for rows in tb.select("table > tr")[2:]:
            StockID = StockName = Remark = []
            CurrRevenue = LastRevenue = YoYRevenue = LastPercent = YoYPercent = CurrCount = LastCount = DiffPercent = 0
            for col1 in rows.select("td:nth-child(1)"):
                StockID = col1.string.strip()
            for col2 in rows.select("td:nth-child(2)"):
                StockName = col2.string.strip()
            for col3 in rows.select("td:nth-child(3)"):
                CurrRevenue = col3.text.replace(",", "")
            for col4 in rows.select("td:nth-child(4)"):
                LastRevenue = col4.text.replace(",", "")
            for col5 in rows.select("td:nth-child(5)"):
                YoYRevenue = col5.text.replace(",", "")
            for col6 in rows.select("td:nth-child(6)"):
                LastPercent = col6.text.replace(",", "").strip()
                if LastPercent.isnumeric():
                    LastPercent
                else:
                    LastPercent = 0       
            for col7 in rows.select("td:nth-child(7)"):
                YoYPercent = col7.text.replace(",", "").strip()
                if YoYPercent.isnumeric():
                    YoYPercent
                else:
                    YoYPercent = 0
            for col8 in rows.select("td:nth-child(8)"):
                CurrCount = col8.text.replace(",", "")
            for col9 in rows.select("td:nth-child(9)"):
                LastCount = col9.text.replace(",", "")
            for col10 in rows.select("td:nth-child(10)"):
                DiffPercent = col10.text.replace(",", "").strip()
                if DiffPercent.isnumeric():
                    DiffPercent
                else:
                    DiffPercent = 0
            for col11 in rows.select("td:nth-child(11)"):
                Remark = col11.string.strip().replace("-", "")
            if StockID != []: 
                collect = [yyyymm, StockID, StockName, int(CurrRevenue), int(LastRevenue), int(YoYRevenue), float(LastPercent), float(YoYPercent), int(CurrCount), int(LastCount), float(DiffPercent), Remark, catg]
                data_item.append(collect)
# 寫資料到File
        # df_imcome = pd.DataFrame(data_item, columns = data_head)
        # # print(df_imcome)      
        
        # file_name = "{}_{}".format(catg, period)
        # df_imcome.to_csv("download_data/" + file_name + "_UTF8.csv", encoding = "UTF-8", index = False )
        # df_imcome.to_csv("download_data/" + file_name + "_BIG5.csv", encoding = "BIG5", index = False )
        

# 寫資料到MS SQL(Revenue)        
        SQL_Insert = ("INSERT INTO BIDC.dbo.mopsRevenueByCompany (YearMonth, StockGroup, StockID, Revenue, Remark) VALUES (?, ?, ?, ?, ?);")
        SQL_Delete = ("DELETE FROM BIDC.dbo.mopsRevenueByCompany WHERE YearMonth = '" + yyyymm + "' AND StockGroup = '" + catg + "'")

        # 先刪資料
        cursor.execute(SQL_Delete)
        conn_sql.commit()
        # Insart資料
        for list in data_item:
            value = [ list[0], list[12], list[1], list[3]*1000, list[11] ]
            cursor.execute(SQL_Insert, value)
            conn_sql.commit()
        print(yyyymm + "(" + catg +")" + "Update Complete!!")

conn_sql.close()
