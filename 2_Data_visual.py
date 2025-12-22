import pandas as pd
import numpy as np
import dash
import glob
import os
import re
from dash import dcc,html,Dash,Input,Output
import plotly.graph_objects as go


class  SiteProcess:
    def __init__ (self,file_path):
        self.df = pd.read_csv(file_path)
        self.header = []
        self.serial_number = None
        self.config = None
        self.upper_limit_row = None
        self.lower_limit_row =  None

    def process_site(self):
        self.header = {'serial_header':'SerialNumber','config_header':'BUILD_MATRIX_CONFIG'}
        self.serial_number = self.df.iloc[:,2]
        self.config = self.df.iloc[:,3]

        try:
            self.upper_limit_row = self.df.iloc[0, 19:]
            self.lower_limit_row = self.df.iloc[1, 19:]
        except:
            self.upper_limit_row = None
            self.lower_limit_row = None

class DataVisual:
    def __init__(self,process,file_path):
        self.df = process.df
        self.file_path = file_path
        self.column_names = self.df.columns.tolist()
    def load_data(self):
        y_data = self.df.iloc[3:,19:]
        raw_columns = self.df.columns[19:]
        self.test_columns = self.format_column_names(raw_columns)
        return y_data,self.test_columns
    def create_plot_data(self):
        y_data, test_columns = self.load_data()
        serial_number = self.df.iloc[:, 2]
        config_data = self.df.iloc[:,3]
        create_dataframe = pd.concat([serial_number,config_data,y_data],axis=1)
        return create_dataframe

    def draw_chart(self):
        # 1. 数据准备
        plot_data = self.create_plot_data()
        x_axis_labels = self.test_columns
        #获取上下限数据系列（作为参考线）
        upper_limit_data = self.df.iloc[0, 19:] if self.df.shape[0] > 1 else None
        lower_limit_data = self.df.iloc[1, 19:] if self.df.shape[0] > 2 else None

        # 2. 创建图表对象
        fig = go.Figure()

        # 3. 添加上下限数据系列（作为参考线）
        if upper_limit_data is not None:
            fig.add_trace(go.Scatter(
                x=x_axis_labels,
                y=upper_limit_data.values,
                mode='lines',
                name='上限',
                line=dict(color='red', width=2, dash='dash'),
                showlegend = False
            ))

        if lower_limit_data is not None:
            fig.add_trace(go.Scatter(
                x=x_axis_labels,
                y=lower_limit_data.values,
                mode='lines',
                name='下限',
                line=dict(color='red', width=2, dash='dash'),
                showlegend = False
            ))
        # 4. 添加数据系列
        if len(plot_data) > 0 and len(x_axis_labels) > 0:
            # 获取Y数据列（从第3列开始，跳过SN和Config）
            y_columns = plot_data.columns[3:]
            # 确保数据维度匹配
            if len(x_axis_labels) > 0 and len(y_columns) > 0:
                # 统计每个SerialNumber出现的次数
                serial_counts = {}
                for index, row in plot_data.iterrows():
                    if not row[2:].isnull().all():      # 只要不是全部为空值就处理
                        sn = row.iloc[0]  # SerialNumber
                        if sn not in serial_counts:
                            serial_counts[sn] = 0
                        serial_counts[sn] += 1
                # 记录每个SerialNumber是否已在图例中显示
                serial_shown = {}
                # 为不同SerialNumber分配颜色
                serial_colors = {}
                color_palette = [
                    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
                color_index = 0
                # 为每一行数据创建一条线
                for index, row in plot_data.iterrows():
                    if not row[2:].isnull().any():
                        sn = row.iloc[0]  # SerialNumber
                        config = row.iloc[1]

                        # 为SerialNumber分配颜色
                        if sn not in serial_colors:
                            serial_colors[sn] = color_palette[color_index % len(color_palette)]
                            color_index += 1

                        # 确定图例名称（基于SerialNumber）
                        if serial_counts[sn] > 1:
                            legend_name = f"{sn}({serial_counts[sn]})"
                        else:
                            legend_name = str(sn)

                        # 确定是否在图例中显示
                        show_in_legend = False
                        if sn not in serial_shown:
                            serial_shown[sn] = True
                            show_in_legend = True

                        fig.add_trace(go.Scatter(
                            x=x_axis_labels,
                            y=row[2:].values,
                            mode='lines+markers',
                            name=legend_name,
                            legendgroup=str(sn),  # 将相同SerialNumber归为一组
                            showlegend=show_in_legend,
                            line=dict(width=2, color=serial_colors[sn]),
                            marker=dict(size=6, color=serial_colors[sn]),
                            hovertemplate=
                            "<b>SN</b>: %{meta[0]}<br>" +
                            "<b>Config</b>: %{meta[1]}<br>" +
                            "<b>Band</b>: %{x}<br>" +
                            "<b>Value</b>: %{y}<br>" +
                            "<extra></extra>",
                            meta=[sn, config]
                        ))

        # 5. 设置图表布局
        fig.update_layout(
            title=dict(
                        text=os.path.splitext(os.path.basename(self.file_path))[0],
                        x=0.5,
                        xanchor='center',
                        font=dict(
                            size=22,
                            color='black',
                            family='Times New Roman',
                            weight = 'bold',
                        )
            ),
            template="plotly_white",
            yaxis = dict(
                autorange = True,
                automargin = True,
            ),

        )
        return fig

    def format_column_names(self, columns):
        """格式化列名，提取关键信息"""
        formatted = []
        for col in columns:
            if pd.isna(col):
                formatted.append("Unknown")
            elif ':' in str(col):
                # 从复杂字符串中提取有用信息
                parts = str(col).split(':')
                # 提取channel值等关键信息
                if 'channel=' in str(col):
                    # 提取channel的具体数值
                    channel_part = [p for p in parts if 'channel=' in p][0]
                    channel_value = channel_part.split('=')[1]
                    formatted.append(f"Channel {channel_value}")
                # 提取freq的值
                elif 'freq=' in str(col):
                    freq_part = [p for p in parts if 'freq=' in p][0]
                    #使用正则表达式匹配频率值和可选单位
                    match = re.search(r"freq=([\d.]+)([A-Za-z]*)",freq_part)
                    if match:
                        freq_value = float(match.group(1))
                        unit = match.group(2)
                        if unit:
                            formatted.append(f"freq {freq_value:.2f}{unit}")
                        else:
                            formatted.append(f"freq {freq_value:.2f}")
                    else:
                        freq_value = freq_part.split('=')[1]
                        try:
                            freq_num = float(freq_value)
                            formatted.append(f"freq {freq_num:.2f}")
                        except ValueError:
                            formatted.append(f"freq {freq_value}")
                else:
                    formatted.append(parts[-2])
            else:
                formatted.append(str(col))
        return formatted


def create_dash_app():
    #获取文件夹下所有CSV文件
    csv_files = glob.glob("extracted_data/*.csv")
    # 为每个文件创建图表
    graphs = []
    for file_path in csv_files:
        try:
            # 处理每个CSV文件
            processor = SiteProcess(file_path)
            processor.process_site()
            visual = DataVisual(processor,file_path)
            fig = visual.draw_chart()
            # 添加文件名作为标题
            # file_name = os.path.basename(file_path)
            graphs.extend([
                html.H2(
                        # file_name,
                        style={"text-align": "center", "margin-top": "30px"}),
                dcc.Graph(figure=fig,
                                config={
                                    'scrollZoom':True,
                                    'displayModeBar':True,
                                })

            ])
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
    app = Dash(__name__)
    app.layout = html.Div([
        html.H1("T11_P1_Station",style={"text-align": "center"}),] + graphs,)
    return app


if __name__ == '__main__':

    app = create_dash_app()
    app.run(debug=True,port=8050)
