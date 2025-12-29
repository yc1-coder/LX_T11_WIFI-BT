import pandas as pd
import glob
import dash
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
        self.config = self.df.iloc[:,4]

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
    def load_data(self):                             #提取测试数据
        y_data = self.df.iloc[3:,19:]
        raw_columns = self.df.columns[19:]
        self.test_columns = self.format_column_names(raw_columns)
        return y_data,self.test_columns

    def create_plot_data(self):                 #SN、Config、Data拼接到一起
        y_data, test_columns = self.load_data()
        serial_number = self.df.iloc[:, 2]
        config_data = self.df.iloc[:,4]
        create_dataframe = pd.concat([serial_number,config_data,y_data],axis=1)
        return create_dataframe


    def draw_chart(self):                          #绘制图表
        # 1. 数据准备
        plot_data = self.create_plot_data()
        x_axis_labels = self.test_columns
        # 获取上下限数据系列（作为参考线）
        # upper_limit_data = self.df.iloc[0, 19:] if self.df.shape[0] > 1 else None
        # lower_limit_data = self.df.iloc[1, 19:] if self.df.shape[0] > 2 else None
        #强制转换数值类型（最终Bug,尼玛的,老子找了一上午）
        upper_limit_data = pd.to_numeric(self.df.iloc[0, 19:], errors='coerce') if self.df.shape[0] > 1 else None
        lower_limit_data = pd.to_numeric(self.df.iloc[1, 19:], errors='coerce') if self.df.shape[0] > 2 else None

        # 2. 创建图表对象
        fig = go.Figure()
        # 3. 添加上下限数据系列（作为参考线）
        if upper_limit_data is not None:
            fig.add_trace(go.Scatter(
                x=x_axis_labels,
                y=upper_limit_data.values,
                mode='lines',
                name='Upper Limit',
                line=dict(color='red', width=2, dash='dash'),
                showlegend=True
            ))
        if lower_limit_data is not None:
            fig.add_trace(go.Scatter(
                x=x_axis_labels,
                y=lower_limit_data.values,
                mode='lines',
                name='Lower Limit',
                line=dict(color='red', width=2, dash='dash'),
                showlegend=True
            ))
        # 4. 添加数据系列
        if len(plot_data) > 0 and len(x_axis_labels) > 0:
            # 获取Y数据列（从第3列开始，跳过SN和Config）
            y_columns = plot_data.columns[2:]
            # 确保数据维度匹配
            if len(x_axis_labels) > 0 and len(y_columns) > 0:
                # 统计每个Config出现的次数
                config_counts = {}
                for index, row in plot_data.iterrows():
                    if not row[2:].isnull().all():  # 只要不是全部为空值就处理
                        config = row.iloc[1]         # Config
                        if config not in config_counts:
                            config_counts[config] = 0
                        config_counts[config] += 1
                # 记录每个Config是否已在图例中显示
                config_shown = {}
                # 为不同Config分配颜色
                config_colors = {}
                color_palette = [
                    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
                color_index = 0
                # 为每一行数据创建一条线
                for index, row in plot_data.iterrows():
                    if not row[2:].isnull().all():
                        sn = row.iloc[0]  # SerialNumber
                        config = row.iloc[1]  # Config
                        # 为Config分配颜色
                        if config not in config_colors:
                            config_colors[config] = color_palette[color_index % len(color_palette)]
                            color_index += 1
                        # 确定图例名称（基于Config）
                        if config_counts[config] > 1:
                            legend_name = f"{config}({config_counts[config]})"
                        else:
                            legend_name = str(config)
                        # 确定是否在图例中显示
                        show_in_legend = False
                        if config not in config_shown:
                            config_shown[config] = True
                            show_in_legend = True

                        fig.add_trace(go.Scatter(
                            x=x_axis_labels,
                            y=row[2:].values,
                            mode='lines+markers',
                            name=legend_name,
                            legendgroup=str(config),  # 将相同Config归为一组
                            showlegend=show_in_legend,
                            line=dict(width=2, color=config_colors[config]),
                            marker=dict(size=6, color=config_colors[config]),
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
            template="plotly_white",
            yaxis=dict(
                autorange=True,
                automargin=True,
            ),
        )
        return fig


    def format_column_names(self, columns):
        """格式化列名，提取关键信息"""
        formatted = []
        for col in columns:
            if pd.isna(col):
                formatted.append("Unknown")
            else:
                col_str = str(col)
                # 匹配 BT/WIFI 格式：BT_RX-2480-3DH5--70_BER
                parts = col_str.split('-')
                if len(parts) >= 2 and any(parts[0].startswith(t) for t in ['BT', 'WIFI']):
                    # 提取中间三个部分：频率-调制方式-参数
                    if len(parts) >= 4:
                        # 第二部分是频率，第三部分是调制方式，第四部分是参数
                        freq = parts[1]  # 频率
                        modulation = parts[2]  # 调制方式
                        param = parts[3]  # 参数（可能为空）

                        # 检查第四部分是否为空，如果为空则取第五部分
                        if not param and len(parts) > 4:
                            param = parts[4]

                        # 构建结果字符串
                        if freq and modulation:
                            if param:
                                formatted.append(f"{freq}-{modulation}-{param}")
                            else:
                                formatted.append(f"{freq}-{modulation}")
                        else:
                            formatted.append(col_str)
                    elif len(parts) == 3:
                        # 如果只有三个部分，返回频率和调制方式
                        freq = parts[1]
                        modulation = parts[2]
                        formatted.append(f"{freq}-{modulation}")
                    else:
                        formatted.append(col_str)
                else:
                    # 对于其他格式，返回原字符串
                    formatted.append(col_str)
        return formatted


def create_dash_app():
    # 获取文件夹下所有CSV文件
    csv_files = glob.glob("extracted_data/*.csv")
    # 为每个文件创建图表
    graphs = []
    # 存储图表ID列表用于回调
    graph_ids = []

    for file_path in csv_files:
        try:
            # 处理每个CSV文件
            processor = SiteProcess(file_path)
            processor.process_site()
            visual = DataVisual(processor, file_path)
            fig = visual.draw_chart()
            # 添加文件名作为标题
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            graph_id = f"graph-{os.path.basename(file_path).replace('.', '_').replace('-', '_')}"
            y_min_id = f"y-min-{os.path.basename(file_path).replace('.', '_').replace('-', '_')}"
            y_max_id = f"y-max-{os.path.basename(file_path).replace('.', '_').replace('-', '_')}"
            store_id = f"store-{os.path.basename(file_path).replace('.', '_').replace('-', '_')}"

            graphs.extend([
                html.H2(
                    file_name,
                    style={"text-align": "center", "margin-top": "30px"}),
                # 添加Y轴范围控制输入框
                html.Div([
                    html.Label("y_start:", style={"margin-right": "10px"}),
                    dcc.Input(id=y_min_id,
                              type="number", placeholder="最小值",
                              style={"margin-right": "20px", "width": "100px"}),
                    html.Label("y_end:", style={"margin-right": "10px"}),
                    dcc.Input(id=y_max_id,
                              type="number", placeholder="最大值",
                              style={"margin-right": "20px", "width": "100px"}),
                    html.Button("apply", id=f"apply-{os.path.basename(file_path).replace('.', '_').replace('-', '_')}",
                                n_clicks=0, style={"margin-right": "20px"}),
                ], style={"margin": "10px", "display": "flex", "align-items": "center"}),
                dcc.Store(id=store_id, data=fig.to_dict()),  # 存储原始图表数据
                dcc.Graph(
                    id=graph_id,
                    figure=fig,
                    config={
                        'scrollZoom': True,
                        'displayModeBar': True,
                    }
                )
            ])
            graph_ids.append((graph_id, y_min_id, y_max_id, store_id, file_path))
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")

    app = Dash(__name__)

    # 为每个图表添加回调函数来控制Y轴范围
    for graph_id, y_min_id, y_max_id, store_id, file_path in graph_ids:
        @app.callback(
            Output(graph_id, 'figure'),
            [Input(f"apply-{os.path.basename(file_path).replace('.', '_').replace('-', '_')}", 'n_clicks')],
            [dash.dependencies.State(y_min_id, 'value'),
             dash.dependencies.State(y_max_id, 'value'),
             dash.dependencies.State(store_id, 'data')]
        )
        def update_y_range(n_clicks, y_min, y_max, original_fig_data):
            if n_clicks > 0 and original_fig_data:
                # 从存储的数据创建图表对象
                fig = go.Figure(data=original_fig_data['data'])

                # 恢复原始布局（除了Y轴）
                fig.update_layout(
                    template=original_fig_data['layout']['template'],
                )

                # 更新Y轴范围
                yaxis_range = {}
                if y_min is not None and y_max is not None:
                    # 如果两个值都提供，设置为指定范围
                    yaxis_range['range'] = [y_min, y_max]
                elif y_min is not None:
                    # 如果只提供最小值，保持当前最大值
                    yaxis_range['range'] = [y_min, y_min + 10]  # 默认范围
                elif y_max is not None:
                    # 如果只提供最大值，保持当前最小值
                    yaxis_range['range'] = [y_max - 10, y_max]  # 默认范围

                if yaxis_range:
                    fig.update_layout(yaxis=yaxis_range)

                return fig
            else:
                # 初始状态或没有点击应用按钮时，返回原始图表
                if original_fig_data:
                    fig = go.Figure(data=original_fig_data['data'])
                    fig.update_layout(
                        template=original_fig_data['layout']['template'],
                    )
                    return fig

            return dash.no_update

    app.layout = html.Div([
                              html.H1("T11_P1_Station", style={"text-align": "center"}),
                          ] + graphs, )

    return app


if __name__ == '__main__':

    app = create_dash_app()
    app.run(debug=True,port=8050)
