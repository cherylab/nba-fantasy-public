import pandas as pd
import requests
import json
from functools import reduce
from datetime import datetime
import openpyxl
import time
from time import mktime
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objs import *
from plotly.graph_objs.scatter.marker import Line
from plotly.subplots import make_subplots
import xlrd
import openpyxl
import numpy as np
import re
from bs4 import BeautifulSoup
import math
import plotly.io as pio
import plot_settings
from multiapp import MultiApp
import streamlit as st
from itertools import product

st.set_page_config(layout='wide')

TEAM_COLORS={'MIL':['#00471B','#EEE1C6'],
            'PHO':['#1D1160','#E56020'],
            'LAC':['#C8102E','#1D428A'],
            'ATL':['#E03A3E','#C1D32F'],
            'BK':['#000000','#999999'], # had to replace white
            'DEN':['#0E2240','#FEC524'],
            'PHI':['#006BB6','#ED174C'],
            'UTA':['#002B5C','#00471B'],
            'DAL':['#00538C','#002B5E'],
            'POR':['#E03A3E','#000000'],
            'WAS':['#002B5C','#E31837'],
             'LAL':['#552583','#FDB927'],
             'BOS':['#007A33','#BA9653'],
             'NYK':['#006BB6','#F58426'],
             'MIA':['#98002E','#F9A01B'],
             'GSW':['#1D428A','#FFC72C'],
             'HOU':['#CE1141','#000000'],
             'TOR':['#CE1141','#000000'],
             'ORL':['#0077C0','#C4CED4'],
             'OKC':['#007AC1','#EF3B24'],
             'IND':['#002D62','#FDBB30'],
             'MEM':['#5D76A9','#12173F'],
             'NOP':['#0C2340','#C8102E'],
             'SAN':['#C4CED4','#000000'],
             'DET':['#C8102E','#1D42BA'],
             'CLE':['#860038','#041E42'],
             'MIN':['#0C2340','#236192'],
             'CHI':['#CE1141','#000000'],
             'CHA':['#1D1160','#1D1160'],
             'NOH':['#031C3E','#CF0829'],
             'NJN':['#0E4794','#E61745'],
             'SEA':['#00552F','#F7BD1F'],
             'SAC':['#5A2D81','#63727A']
            }

# function to get file from google drive
@st.cache
def pull_google_drive(url):
    file_id = url.split('/')[-2]
    dwn_url = "https://drive.google.com/uc?id=" + file_id
    df = pd.read_excel(dwn_url, sheet_name=None)

    sheets = list(df.keys())

    dfs = []

    for i in sheets[2:]:
        df[i] = df[i].rename(columns={'No.': 'player_parrank',
                                      '#': 'player_parrank',
                                      'Player': 'player',
                                      'Avg': 'avgpar',
                                      'Avg PAR': 'avgpar',
                                      'Team': 'team',
                                      'Manager': 'manager',
                                      'Total': 'totpar',
                                      'Draft Pick': 'pick'})

        df[i] = df[i].filter(['player_parrank', 'pick', 'manager', 'player', 'team', 'totpar', 'avgpar'])
        df[i] = df[i].assign(yr=lambda t: i.split(' ')[0])
        dfs.append(df[i])

    dfs = pd.concat(dfs).reset_index(drop=True)
    dfs = dfs.assign(yr=lambda t: t.yr.astype(int),
                     avgpar=lambda t: t.avgpar.fillna(0),
                     games=lambda t: t.totpar / t.avgpar,
                     manager=lambda t: np.where(t.manager == 'Korn', 'Kornstein',
                                                np.where(t.manager == 'Mike Auerbach', 'Auerbach', t.manager)),
                     teamgames=lambda t: t.groupby(['yr', 'team'])['games'].transform('max'),
                     manageryr_avgpick=lambda t: t.groupby(['yr', 'manager'])['pick'].transform('mean'),
                     manageryr_totpar=lambda t: t.groupby(['yr', 'manager'])['totpar'].transform('sum'))

    dfs = dfs.sort_values(by=['yr', 'player_parrank'])
    dfs = dfs.assign(player_avgparrank=lambda t: t.groupby('yr')['avgpar'].transform('rank', ascending=False))
    dfs['player_avgparrank'] = dfs.player_avgparrank.astype(int)

    dfs = dfs[['yr', 'pick', 'player', 'totpar', 'avgpar', 'player_parrank', 'player_avgparrank', 'games',
               'team', 'teamgames', 'manager', 'manageryr_avgpick', 'manageryr_totpar']]

    rename_dict = {'Epstein':'Steve', 'Kaplan':'John', 'Piken':'Mark', 'Levine':'Brian', 'Auerbach':'David',
                   'McGoff':'Chris', 'Newman':'Joey', 'Kornstein':'Evan', 'Jacko':'Aaron', 'Simon':'Michael',
                   'Matt Auerbach':'Owen', 'Chandon':'Wes', 'Thomas':'Tom', 'Steve':'Gary', 'Shawn/Stu':'Stewart',
                   'Jesse':'James', 'Massa':'Lucas'}

    dfs['manager'] = dfs.manager.map(rename_dict)

    return dfs

# load the data from google drive
# url = "https://drive.google.com/file/d/16NBIP4qGtBkNbcxfUElMDjWiADryMa-G/view?usp=sharing"
url = "https://docs.google.com/spreadsheets/d/146iALd467zzri0UCJbtkAmkeTE0WRaR8/edit?usp=sharing&ouid=109079795382383182623&rtpof=true&sd=true"
dfs = pull_google_drive(url)

def player_performance():
    st.title('Historical Player Performance')

    play_exp = st.expander('Annual Player Performance', expanded=True)
    with play_exp:
        st.write('<br>', unsafe_allow_html=True)

        col1, sp, col2, sp, col3 = st.columns((.2,.02,.35,.02,.35))
        metric_sel = col1.radio('PAR metric to use', options=['Total PAR','Average PAR'], index=0)
        yr_pick = col2.selectbox('Year to view', options=sorted(dfs.yr.unique())[::-1], index=0)
        type_sel = col3.selectbox('View filter',
                                  options=['All','First 20 Picks','Last 20 Picks',
                                           f'Top 20 {metric_sel}',f'Bottom 20 {metric_sel}',
                                           f'Top 20 {metric_sel} Over-Performers',
                                           f'Top 20 {metric_sel} Under-Performers'],
                                  index=0)

        st.write('<br>', unsafe_allow_html=True)

        yrdet = dfs.query('yr==@yr_pick').sort_values(by='pick')
        yrdet = yrdet.assign(dif=lambda t: t.pick - t.player_parrank,
                             difavg=lambda t: t.pick - t.player_avgparrank)

        metric_dict = {'Total PAR': ['totpar', 'dif', 'player_parrank'],
                       'Average PAR': ['avgpar', 'difavg', 'player_avgparrank']}

        plot_height = 700
        title_y = .99
        note_y = .86

        if type_sel == 'All':
            plot_height=1800
            title_y=.97
            note_y=.92
            yrdet = yrdet.sort_values(by='pick')
        elif type_sel == 'First 20 Picks':
            yrdet = yrdet.query('pick<=20')
            yrdet = yrdet.sort_values(by='pick')
        elif type_sel == 'Last 20 Picks':
            yrdet = yrdet.sort_values(by='pick', ascending=False)
            yrdet = yrdet[:20]
            yrdet = yrdet.sort_values(by='pick')
        elif type_sel == f'Top 20 {metric_sel}':
            yrdet = yrdet.sort_values(by=metric_dict[metric_sel][0], ascending=False)
            yrdet = yrdet[:20]
            # yrdet = yrdet.sort_values(by='totpar')
        elif type_sel == f'Bottom 20 {metric_sel}':
            yrdet = yrdet.sort_values(by=metric_dict[metric_sel][0])
            yrdet = yrdet[:20]
            yrdet = yrdet.sort_values(by=metric_dict[metric_sel][0], ascending=False)
        elif type_sel == f'Top 20 {metric_sel} Over-Performers':
            yrdet = yrdet[yrdet[metric_dict[metric_sel][1]]>=0].sort_values(by=metric_dict[metric_sel][1], ascending=False)
            yrdet = yrdet[:20]
            yrdet = yrdet.sort_values(by='pick')
        elif type_sel == f'Top 20 {metric_sel} Under-Performers':
            yrdet = yrdet[yrdet[metric_dict[metric_sel][1]]<0].sort_values(by=metric_dict[metric_sel][1], ascending=True)
            # print(yrdet)
            yrdet = yrdet[:20]
            yrdet = yrdet.sort_values(by='pick')

        # create the plot
        rankchg = go.Figure()

        # Add traces
        rankchg.add_trace(go.Scatter(x=yrdet.pick,
                                     y=yrdet.player,
                                     mode='markers',
                                     name='Pick #',
                                     marker_color="#bdbdbd",
                                     marker_size=8,
                                     customdata=np.stack((yrdet.manager, yrdet.team, yrdet[metric_dict[metric_sel][0]],
                                                          yrdet.games), axis=-1),
                                     hovertemplate='%{y}<br>Pick #: %{x}<br>' + f'{metric_sel}' +
                                                   ': %{customdata[2]:.0f}<br><br>'
                                                   'Games Played: %{customdata[3]:.0f}<br>'
                                                   'Team: %{customdata[1]}<br>'
                                                   'Manager: %{customdata[0]}<extra></extra>'))

        rankchg.add_trace(go.Scatter(x=yrdet[metric_dict[metric_sel][2]],
                                     y=yrdet.player,
                                     mode='markers',
                                     name=f'{metric_sel} Rank',
                                     marker_color=TEAM_COLORS['NYK'][0],
                                     marker_size=8,
                                     customdata=np.stack((yrdet.manager, yrdet.team, yrdet[metric_dict[metric_sel][0]],
                                                          yrdet.games), axis=-1),
                                     hovertemplate='%{y}<br>Par Rank: %{x}<br>' + f'{metric_sel}' +
                                                   ': %{customdata[2]:.0f}<br><br>'
                                                   'Games Played: %{customdata[3]:.0f}<br>'
                                                   'Team: %{customdata[1]}<br>'
                                                   'Manager: %{customdata[0]}<extra></extra>'))

        if '20 Picks' in type_sel:
            label_distance = 0.75
        else:
            label_distance = 1.5

        for i in range(len(yrdet)):
            pickval = yrdet['pick'].iloc[i]
            rankval = yrdet[metric_dict[metric_sel][2]].iloc[i]

            diff = pickval - rankval

            if pickval > rankval:
                direction = 'better'
            else:
                direction = 'worse'

            rankchg.add_shape(
                type='line',
                x0=pickval,
                y0=yrdet['player'].iloc[i],
                x1=rankval,
                y1=yrdet['player'].iloc[i],
                line_color="#bdbdbd",
                layer='below'
            )

            rankchg.add_annotation(text=str(diff),
                                   showarrow=False,
                                   y=yrdet['player'].iloc[i],
                                   x=rankval + label_distance if direction == 'worse' else rankval - label_distance,
                                   xanchor='left' if direction =='worse' else 'right',
                                   font_size=12,
                                   font_color=TEAM_COLORS['NYK'][0])

        rankchg.update_yaxes(autorange='reversed',
                             showgrid=True)

        rankchg.update_xaxes(showgrid=False,
                             zeroline=False,
                             ticklabelposition="inside",
                             title=f"Pick # / {metric_sel} Rank")

        rankchg.update_layout(template=plot_settings.nba_template,
                              plot_bgcolor='white',
                              height=plot_height,
                              legend=dict(title="",
                                          yanchor='top',
                                          y=.95,
                                          x=1
                                          ),
                              title=dict(font_size=22,
                                         x=0.05,
                                         y=title_y,
                                         yref='container',
                                         text=f"<b>Player performance vs draft pick: {yr_pick} {metric_sel}</b>"),
                              margin=dict(t=20,
                                          r=160))

        rankchg.add_annotation(text=f"# labels are<br>Pick # - {metric_sel} Rank",
                               align='left',
                               y=note_y,
                               yref='paper',
                               x=1.02,
                               xref='paper',
                               xanchor='left',
                               showarrow=False)

        st.plotly_chart(rankchg, use_container_width=True)

        st.write(f'The above plot compares each player\'s Pick # to their {metric_sel} rank. '
                 f'The {metric_sel} rank is calculated based on all drafted players in that year.<br><br>'
                 f'If the blue dot ({metric_sel} Rank) is to the left of the grey dot (Pick #), that means the '
                 f'player outperformed based on their draft order. If the blue dot is to the right of the grey '
                 f'dot, the player underperformed based on their draft order.<br><br>'
                 f'Note that the number of games played has a large impact on Total PAR, but not Average PAR.',
                 unsafe_allow_html=True)

    table_exp = st.expander('Player History Table', expanded=True)
    with table_exp:
        hist_sel = st.multiselect(label='View years',
                                  options=['All'] + sorted(dfs.yr.unique().tolist()),
                                  default='All')

        player = dfs.groupby(['player', 'yr']).agg({'totpar': 'max', 'pick': 'max'}).unstack()
        player.columns = [f"{x[1]}_{x[0]}" for x in player.columns]

        colorder = [x for x in player.columns if x.endswith('totpar')][::-1] + [x for x in player.columns if
                                                                                x.endswith('pick')][::-1]
        player = player[colorder]
        player = player.sort_values(by=player.columns[0], ascending=False)

        player.columns = [f"{x.split('_')[0]} TotPAR" if x.endswith('totpar') else f"{x.split('_')[0]} Pick" for x in
                          player.columns]

        if 'All' not in hist_sel:
            cols = []

            for y in hist_sel:
                cols.append([x for x in player.columns if x.startswith(str(y))])

            cols = [item for sublist in cols for item in sublist]

            player = player[cols]

        player = player.fillna('0').astype(int)
        player = player.sort_values(by=player.columns[0], ascending=False)
        player = player.reset_index()

        st.dataframe(player, height=600)

def pick_performance():
    st.title('Historical Picks')

    # LOOK AT PICK PERFORMANCE
    pickperf = st.expander('Pick Performance', expanded=True)
    with pickperf:
        pick1, space, pick2, space2 = st.columns((.15, .02, .2, .3))
        cutoff_sel = pick2.number_input('Pick # cutoff',
                                     min_value=1,
                                     max_value=dfs.pick.max(),
                                     value=50,
                                     step=1)

        par_met = pick1.radio('Metric to view', options=['Total PAR', 'Average PAR'], index=0)

        parmet_dict = {'Total PAR':'totpar', 'Average PAR':'avgpar'}

        bypick = dfs.groupby('pick')[parmet_dict[par_met]].mean().to_frame().reset_index()

        bp = px.box(dfs[dfs.pick <= cutoff_sel],
                    x='pick',
                    y=parmet_dict[par_met],
                    #            points=False,
                    labels={'pick': 'Pick', parmet_dict[par_met]: par_met},
                    color_discrete_sequence=[TEAM_COLORS['NYK'][0]])

        bp.update_layout(template=plot_settings.nba_template,
                         title=dict(text=f"<b>Distribution of {par_met.split(' ')[0].lower()} PAR by pick</b>",
                                    font_size=22,
                                    x=.06),
                         plot_bgcolor='white',
                         height=500
                         )

        bp.update_traces(fillcolor="rgba(245,132,38,.5)",
                         line=dict(width=1.5))  # team_colors['NYK'][1])

        bp.update_yaxes(tickformat=",")
        bp.update_xaxes(dtick=5)

        st.plotly_chart(bp, use_container_width=True)

        st.write(f'The above plot shows the distribution of historical {par_met} for players chosen by pick number. '
                 'The middle line in the "box" of each boxplot is the median value. '
                 'The "box" represents all values that fall between the 25th and 75th quartiles.')

    # LOOK AT HISTORICAL PICKS
    byteam = dfs.groupby(['yr', 'team']).agg(
        {'player': 'nunique', 'totpar': 'sum', 'teamgames': 'max', 'pick': ['min', 'max'],
         'player_parrank': ['min', 'max']})
    byteam.columns = [f"{x[0]}_{x[1]}" for x in byteam.columns]
    byteam = byteam.reset_index()

    team_exp = st.expander('Pick History By Team', expanded=True)
    with team_exp:
        team_abr = st.selectbox('Team to view', options=sorted(dfs.team.unique()), index=21)

        tmsum = byteam.query('team==@team_abr')
        tmdet = dfs.query('team==@team_abr')

        bytm = px.scatter(tmdet,
                          x='yr',
                          y='pick',
                          labels={'yr': 'Year', 'pick': 'Draft Pick', 'player': 'Player', 'manager': 'Manager'},
                          hover_data={'yr': True, 'pick': True, 'player': True, 'manager': True})

        bytm.update_traces(mode='markers', marker=dict(size=8, color=TEAM_COLORS[team_abr][0],
                                                       line=dict(color=TEAM_COLORS[team_abr][1],
                                                                 width=1)))

        bytm.update_layout(template=plot_settings.nba_template,
                           plot_bgcolor='white',
                           title=dict(font_size=22,
                                      x=0.05,
                                      y=.98,
                                      text=f"<b>{team_abr} draft picks by year</b>"))

        bytm.update_xaxes(range=[dfs.yr.min() - .5, dfs.yr.max() + .5],
                          showgrid=False,
                          title='',
                          dtick=1)

        st.plotly_chart(bytm, use_container_width=True)

        st.write('The above plot shows all ' + team_abr + ' draft picks by year. '
                                                          'Each data point represents a single drafted player. '
                                                          'Hover over a data point to see more information about that draft pick.')

    yr_exp = st.expander('Pick History By Year', expanded=True)
    with yr_exp:
        yr_pick = st.selectbox('Year to view', options=sorted(dfs.yr.unique())[::-1], index=0)

        yrsum = byteam.query('yr==@yr_pick').sort_values(by='team')
        yrdet = dfs.query('yr==@yr_pick').sort_values(by='team')

        main_colors = {}
        for t in yrdet.team:
            main_colors[t] = TEAM_COLORS[t][0]

        byyr = px.scatter(yrdet,
                          x='team',
                          y='pick',
                          labels={'team': 'Team', 'pick': 'Draft Pick', 'player': 'Player', 'manager': 'Manager'},
                          hover_data={'team': True, 'pick': True, 'player': True, 'manager': True},
                          color='team',
                          color_discrete_map=main_colors)

        byyr.update_traces(mode='markers', marker=dict(size=9,
                                                       line=dict(width=1)))

        byyr.update_layout(template=plot_settings.nba_template,
                           plot_bgcolor='white',
                           title=dict(font_size=22,
                                      x=0.05,
                                      y=.98,
                                      text=f"<b>All draft picks: {yr_pick}</b>"),
                           showlegend=False)

        byyr.update_xaxes(showgrid=False,
                          title='',
                          dtick=1)

        for ser in byyr['data']:
            ser['marker_line_color'] = TEAM_COLORS[ser.legendgroup][1]

        st.plotly_chart(byyr, use_container_width=True)

        st.write('The above plot shows all draft picks for ' + str(yr_pick) + '. Each data point represents a single drafted player, and players are organized by team. Hover over a data point to see more information about that draft pick.')

def manager_performance():
    st.title('Manager Performance')

    finals = dfs.groupby(['yr', 'manager']).agg({'totpar': 'sum', 'pick': 'min'}).reset_index().sort_values(
        by=['yr', 'totpar'],
        ascending=[True, False])
    finals['rank'] = finals.groupby('yr')['totpar'].transform('rank', ascending=False).astype(int)

    rankdf = finals.groupby(['manager', 'rank']).size().to_frame().reset_index()
    rankdf = rankdf.rename(columns={0: 'cnt'})

    temp = pd.DataFrame(list(product(rankdf.manager.unique().tolist(), rankdf['rank'].unique().tolist())),
                        columns=['manager', 'rank']).sort_values(by=['manager', 'rank'])

    rankdf = temp.merge(rankdf, on=['manager', 'rank'], how='left').fillna(0)
    rankdf['cnt'] = rankdf['cnt'].astype(int)
    rankdf['rank'] = rankdf['rank'].astype(str)

    point_exp = st.expander('Historical PAR', expanded=True)
    with point_exp:
        point1, space, point2 = st.columns((.18,.02,1))

        point_sel = point1.radio('Point metric to view', options=['Average PAR', 'Total PAR'], index=0)

        point_dict = {'Average PAR':'avgpar', 'Total PAR':'totpar'}

        ptsum = finals.groupby('manager').agg({'totpar': ['sum', 'mean', 'size']})
        ptsum.columns = [x[1] for x in ptsum.columns]
        ptsum = ptsum.rename(columns={'sum': 'totpar', 'mean': 'avgpar', 'size': 'yrs'})
        ptsum = ptsum.reset_index()
        ptsum = ptsum.sort_values(by=point_dict[point_sel], ascending=False)

        ptfig = make_subplots(specs=[[{"secondary_y": True}]])

        ptfig.add_trace(
            go.Scatter(x=ptsum.manager,
                       y=ptsum[point_dict[point_sel]],
                       name=point_sel,
                       mode='markers',
                       customdata=np.stack((ptsum[point_dict[point_sel]], ptsum.yrs), axis=-1),
                       hovertemplate='Manager: %{x}<br>' + f'{point_sel}' + ': %{customdata[0]:,.2f}<br>Years in Draft: %{customdata[1]}<extra></extra>'),
            secondary_y=True,
        )

        ptfig.add_trace(
            go.Bar(x=ptsum.manager, y=ptsum.yrs, name="# Years"),
            secondary_y=False,
        )

        ptfig.update_layout(template=plot_settings.nba_template,
                            showlegend=False,
                            plot_bgcolor='white',
                            height=500,
                            )

        ptfig.update_yaxes(title_text=point_sel,
                           # title_font_color=plot_settings.nba_template['layout_colorway'][0],
                           title_font_color=TEAM_COLORS['NYK'][0],
                           title_font_size=16,
                           secondary_y=True,
                           showgrid=True,
                           tickformat=",",
                           # tickfont=dict(color=plot_settings.nba_template['layout_colorway'][0]))
                           tickfont=dict(color=TEAM_COLORS['NYK'][0]))

        ptfig.update_yaxes(title_text="# Draft Years",
                           title_font_size=16,
                           secondary_y=False,
                           showgrid=False,
                           title_font_color='#939393',
                           tickfont=dict(color='#939393'))

        ptfig.for_each_trace(
            lambda trace: trace.update(marker_symbol=200,
                                       marker_size=16,
                                       marker_line_width=1.5,
                                       marker_color=TEAM_COLORS['NYK'][0],
                                       marker_line_color=TEAM_COLORS['NYK'][1])
            if trace.name == point_sel
            else trace.update(opacity=0.4,
                              marker_color='lightgrey')
        )

        ptfig.update_layout(
            yaxis=dict(side='right'),
            yaxis2=dict(side='left'),
            title=dict(font_size=22,
                       x=0.05,
                       y=.92,
                       yref='container',
                       text=f"<b>Annual {point_sel.split(' ')[0].lower()} PAR by manager</b>")
        )

        ptfig.add_annotation(text=point_sel,
                             # x=ptfig['data'][0]['x'][0],
                             x=0.1,
                             y=ptfig['data'][0]['y'][0] + 17 if point_sel=='Average PAR' else ptfig['data'][0]['y'][0] + 1200,
                             ax=.6,
                             axref='x',
                             showarrow=True,
                             font_size=14,
                             font_color=TEAM_COLORS['NYK'][0],
                             arrowcolor=TEAM_COLORS['NYK'][0],
                             arrowsize=.75,
                             xref='x',
                             yref='y2')

        point2.plotly_chart(ptfig, use_container_width=True)

        point2.write('The above plot shows each manager\'s annual average PAR or aggregated total PAR. '
                     'The grey bars represent how many drafts that manager participated in and has a large impact on '
                     'a manager\'s total PAR value.')

    point_diff = st.expander('Actual vs Expected Total PAR', expanded=True)
    with point_diff:
        man_sel = st.selectbox('Manager to view',
                               options=sorted(sorted(rankdf.manager.unique())),
                               index=0)

        # reference original dfs
        basics = dfs.groupby(['yr','pick','player','team','manager','player_parrank','player_avgparrank']).agg(
            {'totpar':'first','avgpar':'first'}).reset_index()
        tots = dfs.groupby(['yr', 'player_parrank']).agg({'totpar': 'first'}).reset_index().rename(
            columns={'player_parrank': 'player_parrank_exp', 'totpar': 'totpar_exp'})
        avgs = dfs.groupby(['yr', 'player_avgparrank']).agg({'avgpar': 'first'}).reset_index().rename(
            columns={'player_avgparrank': 'player_avgparrank_exp', 'avgpar': 'avgpar_exp'})

        basics = basics.merge(tots, left_on=['yr', 'pick'], right_on=['yr', 'player_parrank_exp'], how='left').merge(
            avgs, left_on=['yr', 'pick'], right_on=['yr', 'player_avgparrank_exp'], how='left')

        basics = basics.sort_values(by=['yr', 'pick']).reset_index(drop=True)

        ffill_cols = ['player_parrank_exp', 'totpar_exp', 'player_avgparrank_exp', 'avgpar_exp']

        for c in ffill_cols:
            basics[c] = basics[c].fillna(method='ffill')
            basics[c] = basics[c].astype(int)

        exp = basics.groupby(['yr', 'manager']).agg({'totpar': 'sum', 'totpar_exp': 'sum'}).reset_index()

        psn = exp[exp.manager == man_sel].sort_values(by='yr', ascending=False)

        expfig = go.Figure()

        # Add traces
        expfig.add_trace(go.Scatter(x=psn.totpar,
                                    y=psn.yr,
                                    mode='markers',
                                    name='Actual Total PAR',
                                    marker_color=TEAM_COLORS['NYK'][0],
                                    marker_size=10,
                                    customdata=np.stack((psn.manager, psn.yr), axis=-1),
                                    hovertemplate='Manager: %{customdata[0]}<br>Year: %{y}<br>Actual Total PAR: %{x:,.0f}'))

        expfig.add_trace(go.Scatter(x=psn.totpar_exp,
                                    y=psn.yr,
                                    mode='markers',
                                    name='Expected Total PAR',
                                    marker_color="#bdbdbd",
                                    marker_size=10,
                                    customdata=np.stack((psn.manager, psn.yr), axis=-1),
                                    hovertemplate='Manager: %{customdata[0]}<br>Year: %{y}<br>Expected Total PAR: %{x:,.0f}'))

        extremes_x = max(psn.totpar.max(), psn.totpar_exp.max()) - min(psn.totpar.min(), psn.totpar_exp.min())

        if 0 <= extremes_x < 500:
            label_distance = 10
        elif 500 <= extremes_x < 1000:
            label_distance = 20
        elif 1000 <= extremes_x < 1500:
            label_distance = 30
        elif 1500 <= extremes_x < 2300:
            label_distance = 40
        elif 2300 <= extremes_x < 3500:
            label_distance = 50
        elif 3500 <= extremes_x:
            label_distance = 60

        for i in range(len(psn)):
            actual = psn['totpar'].iloc[i]
            expected = psn['totpar_exp'].iloc[i]

            diff = actual - expected

            if actual > expected:
                direction = 'better'
            else:
                direction = 'worse'

            if math.isnan(psn['totpar'].iloc[i]) == False:
                expfig.add_shape(
                    type='line',
                    x0=actual,
                    y0=psn['yr'].iloc[i],
                    x1=expected,
                    y1=psn['yr'].iloc[i],
                    line_color="#bdbdbd",
                    layer='below'
                )

                expfig.add_annotation(text="{:,}".format(int(diff)),
                                      # text="<b>{:,}</b>".format(int(diff)),
                                      showarrow=False,
                                      y=psn['yr'].iloc[i],
                                      x=actual + label_distance if direction == 'better' else actual - label_distance,
                                      xanchor='left' if direction == 'better' else 'right',
                                      font_size=12,
                                      font_color=TEAM_COLORS['NYK'][0])

        expfig.update_yaxes(showgrid=True,
                            # autorange='reversed',
                            dtick=1,
                            title='Draft Year',
                            range=[2004.1,2021.5])

        expfig.update_xaxes(showgrid=False,
                            zeroline=False,
                            tickformat=",",
                            title="Total PAR: Actual & Expected",
                            range=[min(psn.totpar.min(), psn.totpar_exp.min()) - 250,
                                   max(psn.totpar.max(), psn.totpar_exp.max()) + 250])

        expfig.update_layout(template=plot_settings.nba_template,
                             height=800,
                             plot_bgcolor='white',
                             margin=dict(r=200),
                             legend=dict(title="",
                                         yanchor='top',
                                         y=.95,
                                         x=1.0
                                         ),
                             title=dict(font_size=22,
                                        x=0.05,
                                        y=.96,
                                        yref='container',
                                        text=f"<b>Actual total PAR vs expected total PAR by year<br>Manager: {man_sel}</b>"))

        expfig.add_annotation(text="# labels are<br>Actual PAR - Expected PAR",
                              align='left',
                              y=0.85,
                              yref='paper',
                              x=1.02,
                              xref='paper',
                              xanchor='left',
                              showarrow=False)

        st.plotly_chart(expfig, use_container_width=True)

        st.write('The above plot compares a manager\'s actual total PAR against their "expected" total PAR by year. '
                 'All players drafted in a particular year are ranked by their total PAR and this rank is '
                 'matched to each player\'s pick #.<br><br>'
                 'In other words, if LeBron was drafted 2nd, his actual total PAR is compared to the 2nd highest total '
                 'PAR across all players that year.<br><br>A manager\'s actual '
                 'and expected '
                 'total PARs per player are then summed to get the final comparison by year.', unsafe_allow_html=True)

    manage_exp = st.expander('Historical Standings', expanded=True)
    with manage_exp:
        managers_sel = st.multiselect('Compare managers',
                                      options=sorted(rankdf.manager.unique()),
                                      default=['Mark','Steve'])

        rankdf_tmp = rankdf[rankdf.manager.isin(managers_sel)]

        bars = px.bar(rankdf_tmp.sort_values(by=['manager', 'rank']),
                      x='manager',
                      y='cnt',
                      color='rank',
                      text='rank',
                      barmode='group',
                      labels={'manager': 'Manager', 'cnt': '# Draft Years', 'rank': 'Final Standing'},
                      category_orders={'rank': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']})

        bars.update_layout(template=plot_settings.nba_template,
                           bargap=0.15,
                           bargroupgap=0.1,
                           plot_bgcolor='white',
                           height=500,
                           title=dict(font_size=22,
                                      x=0.05,
                                      y=.99,
                                      yref='container',
                                      text=f"<b>Distribution of final standings by manager</b>"), )

        bars.update_traces(marker_color=[x[0] for x in TEAM_COLORS.values()][:rankdf_tmp.manager.nunique()],
                           showlegend=False,
                           textposition='outside')

        bars.update_xaxes(title='')

        bars.update_yaxes(dtick=1)

        bars.add_annotation(text='Note: Bars are labeled with standing number',
                            x=0,
                            xref='paper',
                            xanchor='left',
                            y=1.05,
                            yref='paper',
                            showarrow=False,
                            font_size=14)

        st.plotly_chart(bars, use_container_width=True)

        st.write('This bar plot shows each manager\'s distribution of final standings across all draft years that '
                 'manager participated in. The numerical labels above each bar represent the standing number '
                 'corresponding to that particular bar.')


def create_app_with_pages():
    # CREATE PAGES IN APP
    app = MultiApp()
    app.add_app("Player Performance", player_performance)
    app.add_app('Pick History', pick_performance)
    app.add_app("Manager Performance", manager_performance)


    app.run()

if __name__ == '__main__':
    create_app_with_pages()
