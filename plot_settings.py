import plotly.graph_objs as go

background_color = "white"
grid_color = "#eae7e7"
color_list = ["#CB6102","#464424","#721628","#286D78"]

nba_template = go.layout.Template(
    layout=go.Layout(
        colorway=color_list,
        font={"color": "#4c4c4c", "family": "Avenir"},
        mapbox={"style": "light"},
        paper_bgcolor=background_color,
        plot_bgcolor=background_color,
        hovermode="closest",
        xaxis={
            "automargin": True,
            "gridcolor": grid_color,
            "linecolor": grid_color,
            "ticks": "",
            "zerolinecolor": grid_color,
            "zerolinewidth": 2,
        },
        yaxis={
            "automargin": True,
            "gridcolor": grid_color,
            "linecolor": grid_color,
            "ticks": "",
            "zerolinecolor": grid_color,
            "zerolinewidth": 2,
            "title_standoff": 10,
        },
    )
)