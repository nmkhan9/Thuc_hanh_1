import pandas as pd
from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource, DateRangeSlider, CheckboxGroup, Select, LinearAxis, Range1d, Span
from bokeh.layouts import column, row

# Hàm tính RSI
def calculate_rsi(data, periods=14):
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 📌 Đọc dữ liệu từ file CSV
file_path = r"D:\all_stocks_5yr.csv"
df = pd.read_csv(file_path, parse_dates=["date"])

# 🔄 Đổi tên cột để dễ dùng
df.rename(columns={"date": "Date", "open": "Open", "close": "Close",
                   "high": "High", "low": "Low", "volume": "Volume", "Name": "Stock"}, inplace=True)

# 🔀 Sắp xếp theo ngày
df.sort_values("Date", inplace=True)

# 📌 Ensure Date column is tz-naive datetime64[ns]
df["Date"] = pd.to_datetime(df["Date"], utc=False)

# 📌 Tính RSI cho toàn bộ dữ liệu
df["RSI"] = df.groupby("Stock").apply(lambda x: calculate_rsi(x), include_groups=False).reset_index(level=0, drop=True)

# 📌 Lấy danh sách mã chứng khoán
stock_symbols = sorted(df["Stock"].unique().tolist())

# 🔥 Mặc định hiển thị mã đầu tiên
selected_stock = stock_symbols[0]
filtered_df = df[df["Stock"] == selected_stock]

# ✅ Tạo nguồn dữ liệu ban đầu
source = ColumnDataSource(filtered_df)

# 🎨 Tạo figure chính (giá và volume)
p_main = figure(x_axis_type="datetime", title=f"Stock Prices and Volume: {selected_stock}", height=400, width=800)

# 📈 Trục y chính (bên trái) cho giá
p_main.y_range = Range1d(filtered_df[["Open", "Close", "High", "Low"]].min().min() * 0.95,
                         filtered_df[["Open", "Close", "High", "Low"]].max().max() * 1.05)
colors = {"Open": "blue", "Close": "green", "High": "red", "Low": "purple"}

# Vẽ các đường giá
lines = {col: p_main.line("Date", col, source=source, line_width=2, color=colors[col], legend_label=col) for col in colors.keys()}
for col in ["High", "Low"]:
    lines[col].visible = False

# 📊 Trục y phụ (bên phải) cho Volume
p_main.extra_y_ranges = {"volume": Range1d(start=0, end=filtered_df["Volume"].max() * 1.2)}
p_main.add_layout(LinearAxis(y_range_name="volume", axis_label="Volume"), "right")
p_main.vbar(x="Date", top="Volume", source=source, width=0.9, color="gray", alpha=0.3, y_range_name="volume", legend_label="Volume")

# 🎨 Tạo figure cho RSI (biểu đồ phụ bên dưới)
p_rsi = figure(x_axis_type="datetime", title="RSI", height=200, width=800, x_range=p_main.x_range)
p_rsi.line("Date", "RSI", source=source, line_width=2, color="orange", legend_label="RSI")
p_rsi.y_range = Range1d(0, 100)  # RSI luôn nằm trong khoảng 0-100
p_rsi.add_layout(LinearAxis(axis_label="RSI"), "left")
# 📌 Thêm đường quá bán (RSI=30) và quá mua (RSI=70) bằng Span
oversold_line = Span(location=30, dimension='width', line_color='red', line_dash='dashed', line_width=1)
overbought_line = Span(location=70, dimension='width', line_color='green', line_dash='dashed', line_width=1)
p_rsi.renderers.extend([oversold_line, overbought_line])

# 🗓️ DateRangeSlider để chọn khoảng thời gian
date_slider = DateRangeSlider(title="Select Date Range",
                              start=df["Date"].min(), end=df["Date"].max(),
                              value=(df["Date"].min(), df["Date"].max()), step=1)

# ✅ Checkbox chọn loại giá
checkbox = CheckboxGroup(labels=["Open", "Close", "High", "Low"], active=[0, 1])

# 🔄 Dropdown chọn mã chứng khoán
stock_select = Select(title="Select Stock", value=selected_stock, options=stock_symbols)


# 🔄 Hàm cập nhật dữ liệu
def update(attr, old, new):
    selected_stock = stock_select.value
    # Convert slider values to tz-naive datetime64[ns]
    start = pd.Timestamp(date_slider.value_as_datetime[0]).tz_localize(None)
    end = pd.Timestamp(date_slider.value_as_datetime[1]).tz_localize(None)

    # 📌 Lọc dữ liệu theo khoảng thời gian & mã chứng khoán
    filtered_df = df[(df["Stock"] == selected_stock) & (df["Date"] >= start) & (df["Date"] <= end)]
    source.data = ColumnDataSource.from_df(filtered_df)

    # 🔄 Cập nhật tiêu đề biểu đồ
    p_main.title.text = f"Stock Prices and Volume: {selected_stock}"

    # 🔄 Cập nhật trục y cho giá
    p_main.y_range.start = filtered_df[["Open", "Close", "High", "Low"]].min().min() * 0.95
    p_main.y_range.end = filtered_df[["Open", "Close", "High", "Low"]].max().max() * 1.05

    # 🔄 Cập nhật trục y phụ cho Volume
    p_main.extra_y_ranges["volume"].end = filtered_df["Volume"].max() * 1.2

    # 📊 Cập nhật hiển thị của các đường
    active_labels = [checkbox.labels[i] for i in checkbox.active]
    for col in lines.keys():
        lines[col].visible = col in active_labels


# 🛠️ Gắn sự kiện cập nhật
date_slider.on_change("value", update)
checkbox.on_change("active", update)
stock_select.on_change("value", update)

# 📌 Bố cục giao diện
layout = column(stock_select, row(date_slider), checkbox, p_main, p_rsi)
curdoc().add_root(layout)
curdoc().title = "Stock Price, Volume, and RSI Viewer"