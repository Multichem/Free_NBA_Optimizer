import pulp
import numpy as np
import pandas as pd
import random
import sys
import openpyxl
import re
import time
import streamlit as st
import matplotlib
from  matplotlib.colors import LinearSegmentedColormap
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

st.set_page_config(layout="wide")

tab1, tab2 = st.tabs(["Projections", "Optimizer"])
    
check_list = []
rand_player = 0
boost_player = 0
salaryCut = 0

with tab1:
    hold_container = st.empty()
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
      proj_data = pd.read_json(Projection_URL)
      st.write(proj_data)

with tab2:   
    col1, col2 = st.columns([1, 4])
    
    with col2:
        display_container = st.empty()
    
    st.info('Note that this optimization process aims to create a large set of usable lineups, and not necessarily an exact amount.')
    with col1:
      
        func_choice_select = st.selectbox('Choose optimization', ('Cash', 'Small Field', 'Medium Field', 'Large Field'))
        max_sal = st.number_input('Max Salary', min_value = 35000, max_value = 50000, value = 50000, step = 100)
        min_sal = st.number_input('Min Salary', min_value = 35000, max_value = 49900, value = 49000, step = 100)
        proj_cut = st.number_input('Lowest median allowed', min_value = 0, max_value = 25, value = 10, step = 1)
        ceiling_var = st.number_input('Relative ceiling above:', min_value = 0.0, max_value = 10.0, value = 6.5, step = .1)
        slack_var = st.number_input('Median  Variance in Sims', min_value = 0, max_value = 5, value = 0, step = 1)
        totalRuns_raw = st.number_input('How many Sims', min_value = 1, max_value = 1000, value = 5, step = 1)

    trim_true = 0
    own_trim_var = 50
    trim_var = 5
    trim_dudes = trim_var
    if func_choice_select == 'Cash':
        func_var = 0
    elif func_choice_select == 'Small Field':
        func_var = 1
    elif func_choice_select == 'Medium Field':
        func_var = 2
    elif func_choice_select == 'Large Field':
        func_var = 2
    totalRuns = totalRuns_raw * 5 * (func_var + 1)
    cut_group_1 = []
    cut_group_2 = []
    force_group_1 = []
    force_group_2 = []
    avoid_players = []
    lock_player = []
    lineups = []
    player_pool_raw = []
    
    player_pool = []
    player_count = []
    player_trim_pool = []
    portfolio = pd.DataFrame()
    x = 1

    if st.button('Optimize'):
        with col2:
            with st.spinner('Wait for it...'):
                with hold_container.container():

                        while x <= totalRuns:
                            max_proj = 1000
                            max_own = 1000
                            total_proj = 0
                            total_own = 0

                            if x > 1:
                                if trim_var > 0:
                                    for p_var in range(0,8):
                                        try:
                                            player_pool_raw.append(lineup_final[p_var][0])
                                        except:
                                            pass
                                    [player_pool.append(x) for x in player_pool_raw if x not in player_pool]
                                    for c_var in range(0,len(player_pool)):
                                        player_count.append(player_pool_raw.count(player_pool[c_var]))
                                    player_trim_pool = pd.DataFrame(player_pool, columns = ['Player'])
                                    player_trim_pool['instances'] = player_count
                                    player_trim_pool_check = player_trim_pool
                                    player_trim_pool = player_trim_pool.nlargest(trim_var, ['instances'])

                                    if len(player_trim_pool) > 0:
                                        player_trim_raw = player_trim_pool.sample(n=trim_dudes)
                                        player_trim_list = player_trim_raw['Player'].tolist()
                                elif trim_var == 0:
                                    player_trim_list = []

                            raw_proj_file = optimizer_data
                            raw_flex_file = raw_proj_file.dropna(how='all')
                            raw_flex_file = raw_flex_file.loc[raw_flex_file['Median'] > 0]
                            raw_flex_file = raw_flex_file.loc[raw_flex_file['Median'] > proj_cut]
                            flex_file = raw_flex_file
                            flex_file = flex_file[['Player', 'Team', 'Position', 'Salary', 'Median', 'Own', 'LevX', 'ValX']]
                            flex_file.rename(columns={"Position": "Pos", "Own": "Proj DK Own%"}, inplace = True)
                            flex_file['name_var'] = flex_file['Player']
                            flex_file['lock'] = flex_file['Player'].isin(lock_player)*1
                            if x > 1:
                                flex_file['trim'] = flex_file['Player'].isin(player_trim_list)*1
                            flex_file['force_group_1'] = flex_file['Player'].isin(force_group_1)*1
                            flex_file['force_group_2'] = flex_file['Player'].isin(force_group_2)*1
                            flex_file['cut_group_1'] = flex_file['Player'].isin(cut_group_1)*1
                            flex_file['cut_group_2'] = flex_file['Player'].isin(cut_group_2)*1
                            chalk_file = flex_file.sort_values(by='Proj DK Own%', ascending=False)
                            chalk_group_df = chalk_file.sample(n=10)
                            chalk_group = chalk_group_df['Player'].tolist()
                            flex_file['chalk_group'] = flex_file['Player'].isin(chalk_group)*1
                            lev_file = flex_file.sort_values(by='LevX', ascending=False)
                            lev_group_df = lev_file.sample(n=10)
                            lev_group = lev_group_df['Player'].tolist()
                            flex_file['lev_group'] = flex_file['Player'].isin(lev_group)*1
                            if x > 1:
                                flex_file = flex_file[['Player', 'name_var', 'Team', 'Pos', 'Salary', 'Median', 'Proj DK Own%', 'lock', 'force_group_1', 'force_group_2', 'cut_group_1', 'cut_group_2', 'chalk_group', 'lev_group', 'trim']]
                            elif x == 0:
                                flex_file = flex_file[['Player', 'name_var', 'Team', 'Pos', 'Salary', 'Median', 'Proj DK Own%', 'lock', 'force_group_1', 'force_group_2', 'cut_group_1', 'cut_group_2', 'chalk_group', 'lev_group']]
                            if x > 1:
                                if slack_var > 0:
                                    flex_file['randNumCol'] = np.random.randint(-int(slack_var),int(slack_var), flex_file.shape[0])
                                elif slack_var ==0:
                                    flex_file['randNumCol'] = 0
                            elif x == 1:
                                flex_file['randNumCol'] = 0
                            flex_file['Median'] = flex_file['Median'] + flex_file['randNumCol']
                            flex_file_check = flex_file
                            check_list.append(flex_file['Median'][4])
                            if len(avoid_players) > 0:
                                flex_file = flex_file.loc[~flex_file['Player'].isin(avoid_players)]
                            if len(avoid_teams) > 0:
                                flex_file = flex_file.loc[~flex_file['Team'].isin(avoid_teams)]
                            player_ids = flex_file.index

                            flex_file['DK Ceiling'] = flex_file['Player'].map(DK_dict)
                            flex_file['DK Max'] = flex_file['Player'].map(DK_max_dict)
                            flex_file['Ceiling Value'] = np.where(flex_file['Salary'] <=6000, flex_file['DK Ceiling'] / (flex_file['Salary']/1000), ceiling_var)
                            flex_file_ceilings = flex_file
                            flex_file = flex_file.loc[flex_file['Ceiling Value'] >= ceiling_var]

                            overall_players = flex_file[['Player']]
                            overall_players['player_var_add'] = flex_file.index
                            overall_players['player_var'] = 'player_vars_' + overall_players['player_var_add'].astype(str)

                            player_vars = pulp.LpVariable.dicts("player_vars", flex_file.index, 0, 1, pulp.LpInteger)
                            total_score = pulp.LpProblem("Fantasy_Points_Problem", pulp.LpMaximize)
                            player_match = dict(zip(overall_players['player_var'], overall_players['Player']))
                            player_index_match = dict(zip(overall_players['player_var'], overall_players['player_var_add']))
                            player_own = dict(zip(flex_file['Player'], flex_file['Proj DK Own%']))
                            player_sal = dict(zip(flex_file['Player'], flex_file['Salary']))
                            player_proj = dict(zip(flex_file['Player'], flex_file['Median']))
                            player_pos = dict(zip(flex_file['Player'], flex_file['Pos']))

                            obj_points = {idx: (flex_file['Median'][idx]) for idx in flex_file.index}
                            total_score += sum([player_vars[idx]*obj_points[idx] for idx in flex_file.index])

                            obj_points_max = {idx: (flex_file['Median'][idx]) for idx in flex_file.index}
                            obj_own_max = {idx: (flex_file['Proj DK Own%'][idx]) for idx in flex_file.index}

                            obj_salary = {idx: (flex_file['Salary'][idx]) for idx in flex_file.index}
                            total_score += pulp.lpSum([player_vars[idx]*obj_salary[idx] for idx in flex_file.index]) <= max_sal
                            total_score += pulp.lpSum([player_vars[idx]*obj_salary[idx] for idx in flex_file.index]) >= min_sal

                            if len(lock_player) > 0:
                                for flex in flex_file['lock'].unique():
                                    sub_idx = flex_file[flex_file['lock'] == 1].index
                                    total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) == len(lock_player)

                            if len(force_group_1) > 0:
                                for flex in flex_file['force_group_1'].unique():
                                    sub_idx = flex_file[flex_file['force_group_1'] == 1].index
                                    total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 1

                            if len(force_group_2) > 0:
                                for flex in flex_file['force_group_2'].unique():
                                    sub_idx = flex_file[flex_file['force_group_2'] == 1].index
                                    total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 1

                            if len(cut_group_1) > 0:
                                for flex in flex_file['cut_group_1'].unique():
                                    sub_idx = flex_file[flex_file['cut_group_1'] == 1].index
                                    total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 1

                            if len(cut_group_2) > 0:
                                for flex in flex_file['cut_group_2'].unique():
                                    sub_idx = flex_file[flex_file['cut_group_2'] == 1].index
                                    total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 1

                            if len(player_trim_pool) > 0:
                                for flex in flex_file['trim'].unique():
                                    sub_idx = flex_file[flex_file['trim'] == 1].index
                                    total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) == 0
                            
                            if func_var > 0:
                                for flex in flex_file['lev_group'].unique():
                                    sub_idx = flex_file[flex_file['lev_group'] == 1].index
                                    total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= func_var

                                for flex in flex_file['chalk_group'].unique():
                                    sub_idx = flex_file[flex_file['chalk_group'] == 1].index
                                    total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 6 - func_var
                            
                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'].str.contains("PG")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 1

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'].str.contains("SG")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 1

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'].str.contains("SF")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 1

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'].str.contains("PF")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 1

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'].str.contains("C")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 1

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'].str.contains("C")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 4

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'].str.contains("G")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 3    

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'].str.contains("F")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 3

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[(flex_file['Pos'].str.contains("F")) | (flex_file['Pos'].str.contains("C"))].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 4

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'] == ("PG")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 3

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'] == ("SG")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 3

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'] == ("SF")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 3

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'] == ("PF")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 3

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'] == ("C")].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 2

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[(flex_file['Pos'] == ("PF/C")) | (flex_file['Pos'] == ("C")) | (flex_file['Pos'] == ("PF")) | (flex_file['Pos'] == ("SF/PF"))].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) >= 2

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[(flex_file['Pos'] == ("PG")) | (flex_file['Pos'] == ("C"))].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 4

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[(flex_file['Pos'] == ("SG")) | (flex_file['Pos'] == ("C"))].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 4

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[(flex_file['Pos'] == ("SF")) | (flex_file['Pos'] == ("C"))].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 4

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[(flex_file['Pos'] == ("PF")) | (flex_file['Pos'] == ("C"))].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 4

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[(flex_file['Pos'].str.contains("PF")) | (flex_file['Pos'] == ("C"))].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) <= 4

                            for flex in flex_file['Pos'].unique():
                                sub_idx = flex_file[flex_file['Pos'] != "Var"].index
                                total_score += pulp.lpSum([player_vars[idx] for idx in sub_idx]) == 8

                            player_count = []
                            player_trim = []
                            lineup_list = []

                            total_score += pulp.lpSum([player_vars[idx]*obj_points_max[idx] for idx in flex_file.index]) <= max_proj - .01
                            if trim_true == 1:
                                total_score += pulp.lpSum([player_vars[idx]*obj_points_max[idx] for idx in flex_file.index]) <= (max_own + int(own_trim_var)) - .01

                            total_score.solve()
                            for v in total_score.variables():
                                if v.varValue > 0:
                                    lineup_list.append(v.name)
                            df = pd.DataFrame(lineup_list)
                            df['Names'] = df[0].map(player_match)
                            df['Cost'] = df['Names'].map(player_sal)
                            df['Proj'] = df['Names'].map(player_proj)
                            df['Own'] = df['Names'].map(player_own)
                            total_cost = sum(df['Cost'])
                            total_own = sum(df['Own'])
                            total_proj = sum(df['Proj'])
                            lineup_raw = pd.DataFrame(lineup_list)
                            lineup_raw['Names'] = lineup_raw[0].map(player_match)
                            lineup_raw['value'] = lineup_raw[0].map(player_index_match)
                            lineup_final = lineup_raw.sort_values(by=['value'])
                            del lineup_final[lineup_final.columns[0]]
                            del lineup_final[lineup_final.columns[1]]
                            lineup_final = lineup_final.reset_index(drop=True)
                            lineup_final = lineup_final.T
                            lineup_final['Cost'] = total_cost
                            lineup_final['Proj'] = total_proj
                            lineup_final['Own'] = total_own

                            if total_cost < 50001:
                                lineups.append(lineup_final)

                            max_proj = total_proj
                            max_own = total_own

                            check_list.append(total_proj)

                            portfolio = portfolio.append(lineup_final, ignore_index = True)

                            x += 1
                        
                        portfolio.rename(columns={0: "Player", 1: "Player", 2: "Player", 3: "Player", 4: "Player", 5: "Player", 6: "Player", 7: "Player"}, inplace = True)
                        portfolio = portfolio.dropna()

                        final_outcomes = portfolio
                        final_outcomes.columns = ['Player', 'Player.1', 'Player.2', 'Player.3', 'Player.4', 'Player.5', 'Player.6', 'Player.7', 'Cost', 'Proj', 'Own']

                        final_outcomes['pos.1'] = final_outcomes['Player'].map(pos_dict)
                        final_outcomes['pos.2'] = final_outcomes['Player.1'].map(pos_dict)
                        final_outcomes['pos.3'] = final_outcomes['Player.2'].map(pos_dict)
                        final_outcomes['pos.4'] = final_outcomes['Player.3'].map(pos_dict)
                        final_outcomes['pos.5'] = final_outcomes['Player.4'].map(pos_dict)
                        final_outcomes['pos.6'] = final_outcomes['Player.5'].map(pos_dict)
                        final_outcomes['pos.7'] = final_outcomes['Player.6'].map(pos_dict)
                        final_outcomes['pos.8'] = final_outcomes['Player.7'].map(pos_dict)

                        final_positions = final_outcomes[['pos.1','pos.2','pos.3','pos.4','pos.5','pos.6','pos.7','pos.8']]

                        final_outcomes['PG-count'] = final_positions.apply(lambda x: x.str.contains("PG").sum(), axis=1)
                        final_outcomes['SG-count'] = final_positions.apply(lambda x: x.str.contains("SG").sum(), axis=1)
                        final_outcomes['SF-count'] = final_positions.apply(lambda x: x.str.contains("SF").sum(), axis=1)
                        final_outcomes['PF-count'] = final_positions.apply(lambda x: x.str.contains("PF").sum(), axis=1)
                        final_outcomes['C-count'] = final_positions.apply(lambda x: x.str.contains("C").sum(), axis=1)
                        final_outcomes['two_c'] = final_positions.apply(lambda x: x.str.fullmatch("C").sum(), axis=1)
                        final_outcomes['two_pg'] = final_positions.apply(lambda x: x.str.fullmatch("PG").sum(), axis=1)
                        final_outcomes['two_sg'] = final_positions.apply(lambda x: x.str.fullmatch("SG").sum(), axis=1)
                        final_outcomes['two_sf'] = final_positions.apply(lambda x: x.str.fullmatch("SF").sum(), axis=1)
                        final_outcomes['two_pf'] = final_positions.apply(lambda x: x.str.fullmatch("PF").sum(), axis=1)
                        final_outcomes['SG/SF'] = final_positions.apply(lambda x: x.str.match("SG/SF").sum(), axis=1)
                        final_outcomes['SF/PF'] = final_positions.apply(lambda x: x.str.match("SF/PF").sum(), axis=1)
                        final_outcomes['PG_hard'] = final_positions.apply(lambda x: x.str.fullmatch("PG").sum(), axis=1)
                        final_outcomes['SG_hard'] = final_positions.apply(lambda x: x.str.fullmatch("SG").sum(), axis=1)
                        final_outcomes['SF_hard'] = final_positions.apply(lambda x: x.str.fullmatch("SF").sum(), axis=1)
                        final_outcomes['PF_hard'] = final_positions.apply(lambda x: x.str.fullmatch("PF").sum(), axis=1)

                        final_outcomes['PG'] = 0
                        final_outcomes['SG'] = 0
                        final_outcomes['SF'] = 0
                        final_outcomes['PF'] = 0
                        final_outcomes['C'] = 0
                        final_outcomes['G'] = 0
                        final_outcomes['F'] = 0
                        final_outcomes['UTIL'] = 0

                        final_outcomes['C'] = np.where((final_outcomes['C-count'] == 1) & (final_outcomes['pos.1'].str.contains("C")) & (final_outcomes['C'] == 0), final_outcomes['Player'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['C-count'] == 1) & (final_outcomes['pos.2'].str.contains("C")) & (final_outcomes['C'] == 0), final_outcomes['Player.1'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['C-count'] == 1) & (final_outcomes['pos.3'].str.contains("C")) & (final_outcomes['C'] == 0), final_outcomes['Player.2'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['C-count'] == 1) & (final_outcomes['pos.4'].str.contains("C")) & (final_outcomes['C'] == 0), final_outcomes['Player.3'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['C-count'] == 1) & (final_outcomes['pos.5'].str.contains("C")) & (final_outcomes['C'] == 0), final_outcomes['Player.4'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['C-count'] == 1) & (final_outcomes['pos.6'].str.contains("C")) & (final_outcomes['C'] == 0), final_outcomes['Player.5'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['C-count'] == 1) & (final_outcomes['pos.7'].str.contains("C")) & (final_outcomes['C'] == 0), final_outcomes['Player.6'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['C-count'] == 1) & (final_outcomes['pos.8'].str.contains("C")) & (final_outcomes['C'] == 0), final_outcomes['Player.7'], final_outcomes['C'])

                        final_outcomes['UTIL'] = np.where((final_outcomes['PG_hard'] == 3) & (final_outcomes['Player'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PG_hard'] == 3) & (final_outcomes['Player.1'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PG_hard'] == 3) & (final_outcomes['Player.2'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PG_hard'] == 3) & (final_outcomes['Player.3'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PG_hard'] == 3) & (final_outcomes['Player.4'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PG_hard'] == 3) & (final_outcomes['Player.5'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PG_hard'] == 3) & (final_outcomes['Player.6'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PG_hard'] == 3) & (final_outcomes['Player.7'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['UTIL'])

                        final_outcomes['G'] = np.where((final_outcomes['PG_hard'] >= 2) & (final_outcomes['Player'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player']) & (final_outcomes['UTIL'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['PG_hard'] >= 2) & (final_outcomes['Player.1'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.1']) & (final_outcomes['UTIL'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['PG_hard'] >= 2) & (final_outcomes['Player.2'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.2']) & (final_outcomes['UTIL'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['PG_hard'] >= 2) & (final_outcomes['Player.3'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.3']) & (final_outcomes['UTIL'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['PG_hard'] >= 2) & (final_outcomes['Player.4'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.4']) & (final_outcomes['UTIL'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['PG_hard'] >= 2) & (final_outcomes['Player.5'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.5']) & (final_outcomes['UTIL'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['PG_hard'] >= 2) & (final_outcomes['Player.6'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.6']) & (final_outcomes['UTIL'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['PG_hard'] >= 2) & (final_outcomes['Player.7'].map(pos_dict) == 'PG') & (final_outcomes['PG'] != final_outcomes['Player.7']) & (final_outcomes['UTIL'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['G'])

                        final_outcomes['UTIL'] = np.where((final_outcomes['SG_hard'] == 3) & (final_outcomes['Player'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SG_hard'] == 3) & (final_outcomes['Player.1'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SG_hard'] == 3) & (final_outcomes['Player.2'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SG_hard'] == 3) & (final_outcomes['Player.3'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SG_hard'] == 3) & (final_outcomes['Player.4'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SG_hard'] == 3) & (final_outcomes['Player.5'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SG_hard'] == 3) & (final_outcomes['Player.6'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SG_hard'] == 3) & (final_outcomes['Player.7'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['UTIL'])

                        final_outcomes['G'] = np.where((final_outcomes['SG_hard'] >= 2) & (final_outcomes['Player'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player']) & (final_outcomes['UTIL'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['SG_hard'] >= 2) & (final_outcomes['Player.1'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.1']) & (final_outcomes['UTIL'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['SG_hard'] >= 2) & (final_outcomes['Player.2'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.2']) & (final_outcomes['UTIL'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['SG_hard'] >= 2) & (final_outcomes['Player.3'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.3']) & (final_outcomes['UTIL'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['SG_hard'] >= 2) & (final_outcomes['Player.4'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.4']) & (final_outcomes['UTIL'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['SG_hard'] >= 2) & (final_outcomes['Player.5'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.5']) & (final_outcomes['UTIL'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['SG_hard'] >= 2) & (final_outcomes['Player.6'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.6']) & (final_outcomes['UTIL'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['SG_hard'] >= 2) & (final_outcomes['Player.7'].map(pos_dict) == 'SG') & (final_outcomes['SG'] != final_outcomes['Player.7']) & (final_outcomes['UTIL'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['G'])

                        final_outcomes['UTIL'] = np.where((final_outcomes['SF_hard'] == 3) & (final_outcomes['Player'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SF_hard'] == 3) & (final_outcomes['Player.1'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SF_hard'] == 3) & (final_outcomes['Player.2'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SF_hard'] == 3) & (final_outcomes['Player.3'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SF_hard'] == 3) & (final_outcomes['Player.4'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SF_hard'] == 3) & (final_outcomes['Player.5'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SF_hard'] == 3) & (final_outcomes['Player.6'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['SF_hard'] == 3) & (final_outcomes['Player.7'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['UTIL'])

                        final_outcomes['F'] = np.where((final_outcomes['SF_hard'] >= 2) & (final_outcomes['Player'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player']) & (final_outcomes['UTIL'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['SF_hard'] >= 2) & (final_outcomes['Player.1'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.1']) & (final_outcomes['UTIL'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['SF_hard'] >= 2) & (final_outcomes['Player.2'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.2']) & (final_outcomes['UTIL'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['SF_hard'] >= 2) & (final_outcomes['Player.3'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.3']) & (final_outcomes['UTIL'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['SF_hard'] >= 2) & (final_outcomes['Player.4'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.4']) & (final_outcomes['UTIL'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['SF_hard'] >= 2) & (final_outcomes['Player.5'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.5']) & (final_outcomes['UTIL'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['SF_hard'] >= 2) & (final_outcomes['Player.6'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.6']) & (final_outcomes['UTIL'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['SF_hard'] >= 2) & (final_outcomes['Player.7'].map(pos_dict) == 'SF') & (final_outcomes['SF'] != final_outcomes['Player.7']) & (final_outcomes['UTIL'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['F'])

                        final_outcomes['UTIL'] = np.where((final_outcomes['PF_hard'] == 3) & (final_outcomes['Player'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PF_hard'] == 3) & (final_outcomes['Player.1'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PF_hard'] == 3) & (final_outcomes['Player.2'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PF_hard'] == 3) & (final_outcomes['Player.3'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PF_hard'] == 3) & (final_outcomes['Player.4'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PF_hard'] == 3) & (final_outcomes['Player.5'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PF_hard'] == 3) & (final_outcomes['Player.6'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['PF_hard'] == 3) & (final_outcomes['Player.7'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['UTIL'])

                        final_outcomes['F'] = np.where((final_outcomes['PF_hard'] >= 2) & (final_outcomes['Player'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player']) & (final_outcomes['UTIL'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['PF_hard'] >= 2) & (final_outcomes['Player.1'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.1']) & (final_outcomes['UTIL'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['PF_hard'] >= 2) & (final_outcomes['Player.2'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.2']) & (final_outcomes['UTIL'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['PF_hard'] >= 2) & (final_outcomes['Player.3'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.3']) & (final_outcomes['UTIL'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['PF_hard'] >= 2) & (final_outcomes['Player.4'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.4']) & (final_outcomes['UTIL'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['PF_hard'] >= 2) & (final_outcomes['Player.5'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.5']) & (final_outcomes['UTIL'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['PF_hard'] >= 2) & (final_outcomes['Player.6'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.6']) & (final_outcomes['UTIL'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['PF_hard'] >= 2) & (final_outcomes['Player.7'].map(pos_dict) == 'PF') & (final_outcomes['PF'] != final_outcomes['Player.7']) & (final_outcomes['UTIL'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['F'])

                        final_outcomes['UTIL'] = np.where((final_outcomes['two_c'] == 2) & (final_outcomes['Player'].map(pos_dict) == 'C') & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['two_c'] == 2) & (final_outcomes['Player.1'].map(pos_dict) == 'C') & (final_outcomes['C'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['two_c'] == 2) & (final_outcomes['Player.2'].map(pos_dict) == 'C') & (final_outcomes['C'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['two_c'] == 2) & (final_outcomes['Player.3'].map(pos_dict) == 'C') & (final_outcomes['C'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['two_c'] == 2) & (final_outcomes['Player.4'].map(pos_dict) == 'C') & (final_outcomes['C'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['two_c'] == 2) & (final_outcomes['Player.5'].map(pos_dict) == 'C') & (final_outcomes['C'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['two_c'] == 2) & (final_outcomes['Player.6'].map(pos_dict) == 'C') & (final_outcomes['C'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['two_c'] == 2) & (final_outcomes['Player.7'].map(pos_dict) == 'C') & (final_outcomes['C'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['UTIL'])

                        final_outcomes['PG'] = np.where((final_outcomes['Player'].map(pos_dict) == 'PG') & (final_outcomes['PG'] == 0), final_outcomes['Player'], final_outcomes['PG'])
                        final_outcomes['SG'] = np.where((final_outcomes['Player'].map(pos_dict) == 'SG') & (final_outcomes['SG'] == 0), final_outcomes['Player'], final_outcomes['SG'])
                        final_outcomes['SF'] = np.where((final_outcomes['Player'].map(pos_dict) == 'SF') & (final_outcomes['SF'] == 0), final_outcomes['Player'], final_outcomes['SF'])
                        final_outcomes['PF'] = np.where((final_outcomes['Player'].map(pos_dict) == 'PF') & (final_outcomes['PF'] == 0), final_outcomes['Player'], final_outcomes['PF'])
                        final_outcomes['C'] = np.where((final_outcomes['Player'].map(pos_dict) == 'C') & (final_outcomes['C'] == 0), final_outcomes['Player'], final_outcomes['C'])

                        final_outcomes['PG'] = np.where((final_outcomes['Player.1'].map(pos_dict) == 'PG') & (final_outcomes['PG'] == 0), final_outcomes['Player.1'], final_outcomes['PG'])
                        final_outcomes['SG'] = np.where((final_outcomes['Player.1'].map(pos_dict) == 'SG') & (final_outcomes['SG'] == 0), final_outcomes['Player.1'], final_outcomes['SG'])
                        final_outcomes['SF'] = np.where((final_outcomes['Player.1'].map(pos_dict) == 'SF') & (final_outcomes['SF'] == 0), final_outcomes['Player.1'], final_outcomes['SF'])
                        final_outcomes['PF'] = np.where((final_outcomes['Player.1'].map(pos_dict) == 'PF') & (final_outcomes['PF'] == 0), final_outcomes['Player.1'], final_outcomes['PF'])
                        final_outcomes['C'] = np.where((final_outcomes['Player.1'].map(pos_dict) == 'C') & (final_outcomes['C'] == 0), final_outcomes['Player.1'], final_outcomes['C'])

                        final_outcomes['PG'] = np.where((final_outcomes['Player.2'].map(pos_dict) == 'PG') & (final_outcomes['PG'] == 0), final_outcomes['Player.2'], final_outcomes['PG'])
                        final_outcomes['SG'] = np.where((final_outcomes['Player.2'].map(pos_dict) == 'SG') & (final_outcomes['SG'] == 0), final_outcomes['Player.2'], final_outcomes['SG'])
                        final_outcomes['SF'] = np.where((final_outcomes['Player.2'].map(pos_dict) == 'SF') & (final_outcomes['SF'] == 0), final_outcomes['Player.2'], final_outcomes['SF'])
                        final_outcomes['PF'] = np.where((final_outcomes['Player.2'].map(pos_dict) == 'PF') & (final_outcomes['PF'] == 0), final_outcomes['Player.2'], final_outcomes['PF'])
                        final_outcomes['C'] = np.where((final_outcomes['Player.2'].map(pos_dict) == 'C') & (final_outcomes['C'] == 0), final_outcomes['Player.2'], final_outcomes['C'])

                        final_outcomes['PG'] = np.where((final_outcomes['Player.3'].map(pos_dict) == 'PG') & (final_outcomes['PG'] == 0), final_outcomes['Player.3'], final_outcomes['PG'])
                        final_outcomes['SG'] = np.where((final_outcomes['Player.3'].map(pos_dict) == 'SG') & (final_outcomes['SG'] == 0), final_outcomes['Player.3'], final_outcomes['SG'])
                        final_outcomes['SF'] = np.where((final_outcomes['Player.3'].map(pos_dict) == 'SF') & (final_outcomes['SF'] == 0), final_outcomes['Player.3'], final_outcomes['SF'])
                        final_outcomes['PF'] = np.where((final_outcomes['Player.3'].map(pos_dict) == 'PF') & (final_outcomes['PF'] == 0), final_outcomes['Player.3'], final_outcomes['PF'])
                        final_outcomes['C'] = np.where((final_outcomes['Player.3'].map(pos_dict) == 'C') & (final_outcomes['C'] == 0), final_outcomes['Player.3'], final_outcomes['C'])

                        final_outcomes['PG'] = np.where((final_outcomes['Player.4'].map(pos_dict) == 'PG') & (final_outcomes['PG'] == 0), final_outcomes['Player.4'], final_outcomes['PG'])
                        final_outcomes['SG'] = np.where((final_outcomes['Player.4'].map(pos_dict) == 'SG') & (final_outcomes['SG'] == 0), final_outcomes['Player.4'], final_outcomes['SG'])
                        final_outcomes['SF'] = np.where((final_outcomes['Player.4'].map(pos_dict) == 'SF') & (final_outcomes['SF'] == 0), final_outcomes['Player.4'], final_outcomes['SF'])
                        final_outcomes['PF'] = np.where((final_outcomes['Player.4'].map(pos_dict) == 'PF') & (final_outcomes['PF'] == 0), final_outcomes['Player.4'], final_outcomes['PF'])
                        final_outcomes['C'] = np.where((final_outcomes['Player.4'].map(pos_dict) == 'C') & (final_outcomes['C'] == 0), final_outcomes['Player.4'], final_outcomes['C'])

                        final_outcomes['PG'] = np.where((final_outcomes['Player.5'].map(pos_dict) == 'PG') & (final_outcomes['PG'] == 0), final_outcomes['Player.5'], final_outcomes['PG'])
                        final_outcomes['SG'] = np.where((final_outcomes['Player.5'].map(pos_dict) == 'SG') & (final_outcomes['SG'] == 0), final_outcomes['Player.5'], final_outcomes['SG'])
                        final_outcomes['SF'] = np.where((final_outcomes['Player.5'].map(pos_dict) == 'SF') & (final_outcomes['SF'] == 0), final_outcomes['Player.5'], final_outcomes['SF'])
                        final_outcomes['PF'] = np.where((final_outcomes['Player.5'].map(pos_dict) == 'PF') & (final_outcomes['PF'] == 0), final_outcomes['Player.5'], final_outcomes['PF'])
                        final_outcomes['C'] = np.where((final_outcomes['Player.5'].map(pos_dict) == 'C') & (final_outcomes['C'] == 0), final_outcomes['Player.5'], final_outcomes['C'])

                        final_outcomes['PG'] = np.where((final_outcomes['Player.6'].map(pos_dict) == 'PG') & (final_outcomes['PG'] == 0), final_outcomes['Player.6'], final_outcomes['PG'])
                        final_outcomes['SG'] = np.where((final_outcomes['Player.6'].map(pos_dict) == 'SG') & (final_outcomes['SG'] == 0), final_outcomes['Player.6'], final_outcomes['SG'])
                        final_outcomes['SF'] = np.where((final_outcomes['Player.6'].map(pos_dict) == 'SF') & (final_outcomes['SF'] == 0), final_outcomes['Player.6'], final_outcomes['SF'])
                        final_outcomes['PF'] = np.where((final_outcomes['Player.6'].map(pos_dict) == 'PF') & (final_outcomes['PF'] == 0), final_outcomes['Player.6'], final_outcomes['PF'])
                        final_outcomes['C'] = np.where((final_outcomes['Player.6'].map(pos_dict) == 'C') & (final_outcomes['C'] == 0), final_outcomes['Player.6'], final_outcomes['C'])

                        final_outcomes['PG'] = np.where((final_outcomes['Player.7'].map(pos_dict) == 'PG') & (final_outcomes['PG'] == 0), final_outcomes['Player.7'], final_outcomes['PG'])
                        final_outcomes['SG'] = np.where((final_outcomes['Player.7'].map(pos_dict) == 'SG') & (final_outcomes['SG'] == 0), final_outcomes['Player.7'], final_outcomes['SG'])
                        final_outcomes['SF'] = np.where((final_outcomes['Player.7'].map(pos_dict) == 'SF') & (final_outcomes['SF'] == 0), final_outcomes['Player.7'], final_outcomes['SF'])
                        final_outcomes['PF'] = np.where((final_outcomes['Player.7'].map(pos_dict) == 'PF') & (final_outcomes['PF'] == 0), final_outcomes['Player.7'], final_outcomes['PF'])
                        final_outcomes['C'] = np.where((final_outcomes['Player.7'].map(pos_dict) == 'C') & (final_outcomes['C'] == 0), final_outcomes['Player.7'], final_outcomes['C'])

                        final_outcomes['SF'] = np.where((final_outcomes['SG/SF'] == 1) & (final_outcomes['SF/PF'] == 1) & (final_outcomes['PF_hard'] >= 1) & (final_outcomes['Player'].map(pos_dict) == 'SF/PF'), final_outcomes['Player'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SG/SF'] == 1) & (final_outcomes['SF/PF'] == 1) & (final_outcomes['PF_hard'] >= 1) & (final_outcomes['Player.1'].map(pos_dict) == 'SF/PF'), final_outcomes['Player.1'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SG/SF'] == 1) & (final_outcomes['SF/PF'] == 1) & (final_outcomes['PF_hard'] >= 1) & (final_outcomes['Player.2'].map(pos_dict) == 'SF/PF'), final_outcomes['Player.2'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SG/SF'] == 1) & (final_outcomes['SF/PF'] == 1) & (final_outcomes['PF_hard'] >= 1) & (final_outcomes['Player.3'].map(pos_dict) == 'SF/PF'), final_outcomes['Player.3'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SG/SF'] == 1) & (final_outcomes['SF/PF'] == 1) & (final_outcomes['PF_hard'] >= 1) & (final_outcomes['Player.4'].map(pos_dict) == 'SF/PF'), final_outcomes['Player.4'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SG/SF'] == 1) & (final_outcomes['SF/PF'] == 1) & (final_outcomes['PF_hard'] >= 1) & (final_outcomes['Player.5'].map(pos_dict) == 'SF/PF'), final_outcomes['Player.5'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SG/SF'] == 1) & (final_outcomes['SF/PF'] == 1) & (final_outcomes['PF_hard'] >= 1) & (final_outcomes['Player.6'].map(pos_dict) == 'SF/PF'), final_outcomes['Player.6'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SG/SF'] == 1) & (final_outcomes['SF/PF'] == 1) & (final_outcomes['PF_hard'] >= 1) & (final_outcomes['Player.7'].map(pos_dict) == 'SF/PF'), final_outcomes['Player.7'], final_outcomes['SF'])

                        final_outcomes['PG'] = np.where((final_outcomes['PG-count'] == 1) & (final_outcomes['pos.1'].str.contains("PG")) & (final_outcomes['PG'] == 0), final_outcomes['Player'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['PG-count'] == 1) & (final_outcomes['pos.2'].str.contains("PG")) & (final_outcomes['PG'] == 0), final_outcomes['Player.1'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['PG-count'] == 1) & (final_outcomes['pos.3'].str.contains("PG")) & (final_outcomes['PG'] == 0), final_outcomes['Player.2'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['PG-count'] == 1) & (final_outcomes['pos.4'].str.contains("PG")) & (final_outcomes['PG'] == 0), final_outcomes['Player.3'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['PG-count'] == 1) & (final_outcomes['pos.5'].str.contains("PG")) & (final_outcomes['PG'] == 0), final_outcomes['Player.4'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['PG-count'] == 1) & (final_outcomes['pos.6'].str.contains("PG")) & (final_outcomes['PG'] == 0), final_outcomes['Player.5'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['PG-count'] == 1) & (final_outcomes['pos.7'].str.contains("PG")) & (final_outcomes['PG'] == 0), final_outcomes['Player.6'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['PG-count'] == 1) & (final_outcomes['pos.8'].str.contains("PG")) & (final_outcomes['PG'] == 0), final_outcomes['Player.7'], final_outcomes['PG'])

                        final_outcomes['SG'] = np.where((final_outcomes['SG-count'] == 1) & (final_outcomes['pos.1'].str.contains("SG")) & (final_outcomes['SG'] == 0), final_outcomes['Player'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['SG-count'] == 1) & (final_outcomes['pos.2'].str.contains("SG")) & (final_outcomes['SG'] == 0), final_outcomes['Player.1'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['SG-count'] == 1) & (final_outcomes['pos.3'].str.contains("SG")) & (final_outcomes['SG'] == 0), final_outcomes['Player.2'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['SG-count'] == 1) & (final_outcomes['pos.4'].str.contains("SG")) & (final_outcomes['SG'] == 0), final_outcomes['Player.3'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['SG-count'] == 1) & (final_outcomes['pos.5'].str.contains("SG")) & (final_outcomes['SG'] == 0), final_outcomes['Player.4'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['SG-count'] == 1) & (final_outcomes['pos.6'].str.contains("SG")) & (final_outcomes['SG'] == 0), final_outcomes['Player.5'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['SG-count'] == 1) & (final_outcomes['pos.7'].str.contains("SG")) & (final_outcomes['SG'] == 0), final_outcomes['Player.6'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['SG-count'] == 1) & (final_outcomes['pos.8'].str.contains("SG")) & (final_outcomes['SG'] == 0), final_outcomes['Player.7'], final_outcomes['SG'])

                        final_outcomes['SF'] = np.where((final_outcomes['SF-count'] == 1) & (final_outcomes['pos.1'].str.contains("SF")) & (final_outcomes['SF'] == 0), final_outcomes['Player'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SF-count'] == 1) & (final_outcomes['pos.2'].str.contains("SF")) & (final_outcomes['SF'] == 0), final_outcomes['Player.1'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SF-count'] == 1) & (final_outcomes['pos.3'].str.contains("SF")) & (final_outcomes['SF'] == 0), final_outcomes['Player.2'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SF-count'] == 1) & (final_outcomes['pos.4'].str.contains("SF")) & (final_outcomes['SF'] == 0), final_outcomes['Player.3'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SF-count'] == 1) & (final_outcomes['pos.5'].str.contains("SF")) & (final_outcomes['SF'] == 0), final_outcomes['Player.4'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SF-count'] == 1) & (final_outcomes['pos.6'].str.contains("SF")) & (final_outcomes['SF'] == 0), final_outcomes['Player.5'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SF-count'] == 1) & (final_outcomes['pos.7'].str.contains("SF")) & (final_outcomes['SF'] == 0), final_outcomes['Player.6'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['SF-count'] == 1) & (final_outcomes['pos.8'].str.contains("SF")) & (final_outcomes['SF'] == 0), final_outcomes['Player.7'], final_outcomes['SF'])

                        final_outcomes['PF'] = np.where((final_outcomes['PF-count'] == 1) & (final_outcomes['pos.1'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['PF-count'] == 1) & (final_outcomes['pos.2'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player.1'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['PF-count'] == 1) & (final_outcomes['pos.3'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player.2'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['PF-count'] == 1) & (final_outcomes['pos.4'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player.3'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['PF-count'] == 1) & (final_outcomes['pos.5'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player.4'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['PF-count'] == 1) & (final_outcomes['pos.6'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player.5'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['PF-count'] == 1) & (final_outcomes['pos.7'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player.6'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['PF-count'] == 1) & (final_outcomes['pos.8'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player.7'], final_outcomes['PF'])


                        # #---------- AFTER CHECKING FOR SINGLE INSTANCE POSITIONS ----------#
                        final_outcomes['PG'] = np.where((final_outcomes['pos.1'].str.contains("PG")) & (final_outcomes['pos.1'] == "PG/SG") & (final_outcomes['PG'] == 0), final_outcomes['Player'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['pos.2'].str.contains("PG")) & (final_outcomes['pos.2'] == "PG/SG") & (final_outcomes['PG'] == 0), final_outcomes['Player.1'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['pos.3'].str.contains("PG")) & (final_outcomes['pos.3'] == "PG/SG") & (final_outcomes['PG'] == 0), final_outcomes['Player.2'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['pos.4'].str.contains("PG")) & (final_outcomes['pos.4'] == "PG/SG") & (final_outcomes['PG'] == 0), final_outcomes['Player.3'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['pos.5'].str.contains("PG")) & (final_outcomes['pos.5'] == "PG/SG") & (final_outcomes['PG'] == 0), final_outcomes['Player.4'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['pos.6'].str.contains("PG")) & (final_outcomes['pos.6'] == "PG/SG") & (final_outcomes['PG'] == 0), final_outcomes['Player.5'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['pos.7'].str.contains("PG")) & (final_outcomes['pos.7'] == "PG/SG") & (final_outcomes['PG'] == 0), final_outcomes['Player.6'], final_outcomes['PG'])
                        final_outcomes['PG'] = np.where((final_outcomes['pos.8'].str.contains("PG")) & (final_outcomes['pos.8'] == "PG/SG") & (final_outcomes['PG'] == 0), final_outcomes['Player.7'], final_outcomes['PG'])

                        final_outcomes['SG'] = np.where((final_outcomes['pos.1'].str.contains("SG")) & (final_outcomes['pos.1'] == "PG/SG") & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.2'].str.contains("SG")) & (final_outcomes['pos.2'] == "PG/SG") & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.3'].str.contains("SG")) & (final_outcomes['pos.3'] == "PG/SG") & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.4'].str.contains("SG")) & (final_outcomes['pos.4'] == "PG/SG") & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.5'].str.contains("SG")) & (final_outcomes['pos.5'] == "PG/SG") & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.6'].str.contains("SG")) & (final_outcomes['pos.6'] == "PG/SG") & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.7'].str.contains("SG")) & (final_outcomes['pos.7'] == "PG/SG") & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.8'].str.contains("SG")) & (final_outcomes['pos.8'] == "PG/SG") & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['SG'])

                        final_outcomes['SG'] = np.where((final_outcomes['pos.1'].str.contains("SG")) & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.2'].str.contains("SG")) & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.3'].str.contains("SG")) & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.4'].str.contains("SG")) & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.5'].str.contains("SG")) & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.6'].str.contains("SG")) & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.7'].str.contains("SG")) & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['SG'])
                        final_outcomes['SG'] = np.where((final_outcomes['pos.8'].str.contains("SG")) & (final_outcomes['SG'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['SG'])

                        final_outcomes['SF'] = np.where((final_outcomes['pos.1'] == ("SG/SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.2'] == ("SG/SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.3'] == ("SG/SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.4'] == ("SG/SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.5'] == ("SG/SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.6'] == ("SG/SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.7'] == ("SG/SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.8'] == ("SG/SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['SF'])

                        final_outcomes['SF'] = np.where((final_outcomes['pos.1'] == ("SF/PF")) & (final_outcomes['PF_hard'] == 1) & (final_outcomes['SF'] == 0), final_outcomes['Player'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.2'] == ("SF/PF")) & (final_outcomes['PF_hard'] == 1) & (final_outcomes['SF'] == 0), final_outcomes['Player.1'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.3'] == ("SF/PF")) & (final_outcomes['PF_hard'] == 1) & (final_outcomes['SF'] == 0), final_outcomes['Player.2'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.4'] == ("SF/PF")) & (final_outcomes['PF_hard'] == 1) & (final_outcomes['SF'] == 0), final_outcomes['Player.3'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.5'] == ("SF/PF")) & (final_outcomes['PF_hard'] == 1) & (final_outcomes['SF'] == 0), final_outcomes['Player.4'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.6'] == ("SF/PF")) & (final_outcomes['PF_hard'] == 1) & (final_outcomes['SF'] == 0), final_outcomes['Player.5'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.7'] == ("SF/PF")) & (final_outcomes['PF_hard'] == 1) & (final_outcomes['SF'] == 0), final_outcomes['Player.6'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.8'] == ("SF/PF")) & (final_outcomes['PF_hard'] == 1) & (final_outcomes['SF'] == 0), final_outcomes['Player.7'], final_outcomes['SF'])

                        final_outcomes['SF'] = np.where((final_outcomes['pos.1'] == ("SF/PF")) & (final_outcomes['C-count'] == 4) & (final_outcomes['SF'] == 0), final_outcomes['Player'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.2'] == ("SF/PF")) & (final_outcomes['C-count'] == 4) & (final_outcomes['SF'] == 0), final_outcomes['Player.1'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.3'] == ("SF/PF")) & (final_outcomes['C-count'] == 4) & (final_outcomes['SF'] == 0), final_outcomes['Player.2'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.4'] == ("SF/PF")) & (final_outcomes['C-count'] == 4) & (final_outcomes['SF'] == 0), final_outcomes['Player.3'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.5'] == ("SF/PF")) & (final_outcomes['C-count'] == 4) & (final_outcomes['SF'] == 0), final_outcomes['Player.4'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.6'] == ("SF/PF")) & (final_outcomes['C-count'] == 4) & (final_outcomes['SF'] == 0), final_outcomes['Player.5'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.7'] == ("SF/PF")) & (final_outcomes['C-count'] == 4) & (final_outcomes['SF'] == 0), final_outcomes['Player.6'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.8'] == ("SF/PF")) & (final_outcomes['C-count'] == 4) & (final_outcomes['SF'] == 0), final_outcomes['Player.7'], final_outcomes['SF'])

                        final_outcomes['SF'] = np.where((final_outcomes['pos.1'].str.contains("SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player']) & (final_outcomes['PG'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.2'].str.contains("SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.1']) & (final_outcomes['PG'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.3'].str.contains("SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.2']) & (final_outcomes['PG'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.4'].str.contains("SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.3']) & (final_outcomes['PG'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.5'].str.contains("SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.4']) & (final_outcomes['PG'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.6'].str.contains("SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.5']) & (final_outcomes['PG'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.7'].str.contains("SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.6']) & (final_outcomes['PG'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['SF'])
                        final_outcomes['SF'] = np.where((final_outcomes['pos.8'].str.contains("SF")) & (final_outcomes['SF'] == 0) & (final_outcomes['SG'] != final_outcomes['Player.7']) & (final_outcomes['PG'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['SF'])

                        final_outcomes['PF'] = np.where((final_outcomes['pos.1'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['SF'] != final_outcomes['Player']) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['pos.2'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['SF'] != final_outcomes['Player.1']) & (final_outcomes['C'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['pos.3'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['SF'] != final_outcomes['Player.2']) & (final_outcomes['C'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['pos.4'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['SF'] != final_outcomes['Player.3']) & (final_outcomes['C'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['pos.5'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['SF'] != final_outcomes['Player.4']) & (final_outcomes['C'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['pos.6'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['SF'] != final_outcomes['Player.5']) & (final_outcomes['C'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['pos.7'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['SF'] != final_outcomes['Player.6']) & (final_outcomes['C'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['PF'])
                        final_outcomes['PF'] = np.where((final_outcomes['pos.8'].str.contains("PF")) & (final_outcomes['PF'] == 0) & (final_outcomes['SF'] != final_outcomes['Player.7']) & (final_outcomes['C'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['PF'])

                        final_outcomes['C'] = np.where((final_outcomes['pos.1'].str.contains("C")) & (final_outcomes['C'] == 0) & (final_outcomes['PF'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['pos.2'].str.contains("C")) & (final_outcomes['C'] == 0) & (final_outcomes['PF'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['pos.3'].str.contains("C")) & (final_outcomes['C'] == 0) & (final_outcomes['PF'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['pos.4'].str.contains("C")) & (final_outcomes['C'] == 0) & (final_outcomes['PF'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['pos.5'].str.contains("C")) & (final_outcomes['C'] == 0) & (final_outcomes['PF'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['pos.6'].str.contains("C")) & (final_outcomes['C'] == 0) & (final_outcomes['PF'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['pos.7'].str.contains("C")) & (final_outcomes['C'] == 0) & (final_outcomes['PF'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['C'])
                        final_outcomes['C'] = np.where((final_outcomes['pos.8'].str.contains("C")) & (final_outcomes['C'] == 0) & (final_outcomes['PF'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['C'])

                        #---------- AFTER UNIQUE POSITIONS ARE FILLED ----------#
                        final_outcomes['G'] = np.where((final_outcomes['pos.1'].str.contains("G")) & (~final_outcomes['pos.1'].str.contains("F")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player']) & (final_outcomes['SG'] != final_outcomes['Player']) & (final_outcomes['SF'] != final_outcomes['Player']) & (final_outcomes['PF'] != final_outcomes['Player']) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.2'].str.contains("G")) & (~final_outcomes['pos.2'].str.contains("F")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.1']) & (final_outcomes['SG'] != final_outcomes['Player.1']) & (final_outcomes['SF'] != final_outcomes['Player.1']) & (final_outcomes['PF'] != final_outcomes['Player.1']) & (final_outcomes['C'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.3'].str.contains("G")) & (~final_outcomes['pos.3'].str.contains("F")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.2']) & (final_outcomes['SG'] != final_outcomes['Player.2']) & (final_outcomes['SF'] != final_outcomes['Player.2']) & (final_outcomes['PF'] != final_outcomes['Player.2']) & (final_outcomes['C'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.4'].str.contains("G")) & (~final_outcomes['pos.4'].str.contains("F")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.3']) & (final_outcomes['SG'] != final_outcomes['Player.3']) & (final_outcomes['SF'] != final_outcomes['Player.3']) & (final_outcomes['PF'] != final_outcomes['Player.3']) & (final_outcomes['C'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.5'].str.contains("G")) & (~final_outcomes['pos.5'].str.contains("F")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.4']) & (final_outcomes['SG'] != final_outcomes['Player.4']) & (final_outcomes['SF'] != final_outcomes['Player.4']) & (final_outcomes['PF'] != final_outcomes['Player.4']) & (final_outcomes['C'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.6'].str.contains("G")) & (~final_outcomes['pos.6'].str.contains("F")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.5']) & (final_outcomes['SG'] != final_outcomes['Player.5']) & (final_outcomes['SF'] != final_outcomes['Player.5']) & (final_outcomes['PF'] != final_outcomes['Player.5']) & (final_outcomes['C'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.7'].str.contains("G")) & (~final_outcomes['pos.7'].str.contains("F")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.6']) & (final_outcomes['SG'] != final_outcomes['Player.6']) & (final_outcomes['SF'] != final_outcomes['Player.6']) & (final_outcomes['PF'] != final_outcomes['Player.6']) & (final_outcomes['C'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.8'].str.contains("G")) & (~final_outcomes['pos.8'].str.contains("F")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.7']) & (final_outcomes['SG'] != final_outcomes['Player.7']) & (final_outcomes['SF'] != final_outcomes['Player.7']) & (final_outcomes['PF'] != final_outcomes['Player.7']) & (final_outcomes['C'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['G'])

                        final_outcomes['G'] = np.where((final_outcomes['pos.1'].str.contains("G")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player']) & (final_outcomes['SG'] != final_outcomes['Player']) & (final_outcomes['SF'] != final_outcomes['Player']) & (final_outcomes['PF'] != final_outcomes['Player']) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.2'].str.contains("G")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.1']) & (final_outcomes['SG'] != final_outcomes['Player.1']) & (final_outcomes['SF'] != final_outcomes['Player.1']) & (final_outcomes['PF'] != final_outcomes['Player.1']) & (final_outcomes['C'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.3'].str.contains("G")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.2']) & (final_outcomes['SG'] != final_outcomes['Player.2']) & (final_outcomes['SF'] != final_outcomes['Player.2']) & (final_outcomes['PF'] != final_outcomes['Player.2']) & (final_outcomes['C'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.4'].str.contains("G")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.3']) & (final_outcomes['SG'] != final_outcomes['Player.3']) & (final_outcomes['SF'] != final_outcomes['Player.3']) & (final_outcomes['PF'] != final_outcomes['Player.3']) & (final_outcomes['C'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.5'].str.contains("G")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.4']) & (final_outcomes['SG'] != final_outcomes['Player.4']) & (final_outcomes['SF'] != final_outcomes['Player.4']) & (final_outcomes['PF'] != final_outcomes['Player.4']) & (final_outcomes['C'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.6'].str.contains("G")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.5']) & (final_outcomes['SG'] != final_outcomes['Player.5']) & (final_outcomes['SF'] != final_outcomes['Player.5']) & (final_outcomes['PF'] != final_outcomes['Player.5']) & (final_outcomes['C'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.7'].str.contains("G")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.6']) & (final_outcomes['SG'] != final_outcomes['Player.6']) & (final_outcomes['SF'] != final_outcomes['Player.6']) & (final_outcomes['PF'] != final_outcomes['Player.6']) & (final_outcomes['C'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['G'])
                        final_outcomes['G'] = np.where((final_outcomes['pos.8'].str.contains("G")) & (final_outcomes['G'] == 0) & (final_outcomes['PG'] != final_outcomes['Player.7']) & (final_outcomes['SG'] != final_outcomes['Player.7']) & (final_outcomes['SF'] != final_outcomes['Player.7']) & (final_outcomes['PF'] != final_outcomes['Player.7']) & (final_outcomes['C'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['G'])

                        final_outcomes['F'] = np.where((final_outcomes['pos.1'].str.contains("F")) & (~final_outcomes['pos.1'].str.contains("G")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player']) & (final_outcomes['PG'] != final_outcomes['Player']) & (final_outcomes['SG'] != final_outcomes['Player']) & (final_outcomes['SF'] != final_outcomes['Player']) & (final_outcomes['PF'] != final_outcomes['Player']) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.2'].str.contains("F")) & (~final_outcomes['pos.2'].str.contains("G")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.1']) & (final_outcomes['PG'] != final_outcomes['Player.1']) & (final_outcomes['SG'] != final_outcomes['Player.1']) & (final_outcomes['SF'] != final_outcomes['Player.1']) & (final_outcomes['PF'] != final_outcomes['Player.1']) & (final_outcomes['C'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.3'].str.contains("F")) & (~final_outcomes['pos.3'].str.contains("G")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.2']) & (final_outcomes['PG'] != final_outcomes['Player.2']) & (final_outcomes['SG'] != final_outcomes['Player.2']) & (final_outcomes['SF'] != final_outcomes['Player.2']) & (final_outcomes['PF'] != final_outcomes['Player.2']) & (final_outcomes['C'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.4'].str.contains("F")) & (~final_outcomes['pos.4'].str.contains("G")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.3']) & (final_outcomes['PG'] != final_outcomes['Player.3']) & (final_outcomes['SG'] != final_outcomes['Player.3']) & (final_outcomes['SF'] != final_outcomes['Player.3']) & (final_outcomes['PF'] != final_outcomes['Player.3']) & (final_outcomes['C'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.5'].str.contains("F")) & (~final_outcomes['pos.5'].str.contains("G")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.4']) & (final_outcomes['PG'] != final_outcomes['Player.4']) & (final_outcomes['SG'] != final_outcomes['Player.4']) & (final_outcomes['SF'] != final_outcomes['Player.4']) & (final_outcomes['PF'] != final_outcomes['Player.4']) & (final_outcomes['C'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.6'].str.contains("F")) & (~final_outcomes['pos.6'].str.contains("G")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.5']) & (final_outcomes['PG'] != final_outcomes['Player.5']) & (final_outcomes['SG'] != final_outcomes['Player.5']) & (final_outcomes['SF'] != final_outcomes['Player.5']) & (final_outcomes['PF'] != final_outcomes['Player.5']) & (final_outcomes['C'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.7'].str.contains("F")) & (~final_outcomes['pos.7'].str.contains("G")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.6']) & (final_outcomes['PG'] != final_outcomes['Player.6']) & (final_outcomes['SG'] != final_outcomes['Player.6']) & (final_outcomes['SF'] != final_outcomes['Player.6']) & (final_outcomes['PF'] != final_outcomes['Player.6']) & (final_outcomes['C'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.8'].str.contains("F")) & (~final_outcomes['pos.8'].str.contains("G")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.7']) & (final_outcomes['PG'] != final_outcomes['Player.7']) & (final_outcomes['SG'] != final_outcomes['Player.7']) & (final_outcomes['SF'] != final_outcomes['Player.7']) & (final_outcomes['PF'] != final_outcomes['Player.7']) & (final_outcomes['C'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['F'])

                        final_outcomes['F'] = np.where((final_outcomes['pos.1'].str.contains("F")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player']) & (final_outcomes['PG'] != final_outcomes['Player']) & (final_outcomes['SG'] != final_outcomes['Player']) & (final_outcomes['SF'] != final_outcomes['Player']) & (final_outcomes['PF'] != final_outcomes['Player']) & (final_outcomes['C'] != final_outcomes['Player']), final_outcomes['Player'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.2'].str.contains("F")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.1']) & (final_outcomes['PG'] != final_outcomes['Player.1']) & (final_outcomes['SG'] != final_outcomes['Player.1']) & (final_outcomes['SF'] != final_outcomes['Player.1']) & (final_outcomes['PF'] != final_outcomes['Player.1']) & (final_outcomes['C'] != final_outcomes['Player.1']), final_outcomes['Player.1'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.3'].str.contains("F")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.2']) & (final_outcomes['PG'] != final_outcomes['Player.2']) & (final_outcomes['SG'] != final_outcomes['Player.2']) & (final_outcomes['SF'] != final_outcomes['Player.2']) & (final_outcomes['PF'] != final_outcomes['Player.2']) & (final_outcomes['C'] != final_outcomes['Player.2']), final_outcomes['Player.2'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.4'].str.contains("F")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.3']) & (final_outcomes['PG'] != final_outcomes['Player.3']) & (final_outcomes['SG'] != final_outcomes['Player.3']) & (final_outcomes['SF'] != final_outcomes['Player.3']) & (final_outcomes['PF'] != final_outcomes['Player.3']) & (final_outcomes['C'] != final_outcomes['Player.3']), final_outcomes['Player.3'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.5'].str.contains("F")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.4']) & (final_outcomes['PG'] != final_outcomes['Player.4']) & (final_outcomes['SG'] != final_outcomes['Player.4']) & (final_outcomes['SF'] != final_outcomes['Player.4']) & (final_outcomes['PF'] != final_outcomes['Player.4']) & (final_outcomes['C'] != final_outcomes['Player.4']), final_outcomes['Player.4'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.6'].str.contains("F")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.5']) & (final_outcomes['PG'] != final_outcomes['Player.5']) & (final_outcomes['SG'] != final_outcomes['Player.5']) & (final_outcomes['SF'] != final_outcomes['Player.5']) & (final_outcomes['PF'] != final_outcomes['Player.5']) & (final_outcomes['C'] != final_outcomes['Player.5']), final_outcomes['Player.5'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.7'].str.contains("F")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.6']) & (final_outcomes['PG'] != final_outcomes['Player.6']) & (final_outcomes['SG'] != final_outcomes['Player.6']) & (final_outcomes['SF'] != final_outcomes['Player.6']) & (final_outcomes['PF'] != final_outcomes['Player.6']) & (final_outcomes['C'] != final_outcomes['Player.6']), final_outcomes['Player.6'], final_outcomes['F'])
                        final_outcomes['F'] = np.where((final_outcomes['pos.8'].str.contains("F")) & (final_outcomes['F'] == 0) & (final_outcomes['G'] != final_outcomes['Player.7']) & (final_outcomes['PG'] != final_outcomes['Player.7']) & (final_outcomes['SG'] != final_outcomes['Player.7']) & (final_outcomes['SF'] != final_outcomes['Player.7']) & (final_outcomes['PF'] != final_outcomes['Player.7']) & (final_outcomes['C'] != final_outcomes['Player.7']), final_outcomes['Player.7'], final_outcomes['F'])

                        # #---------- FILL UNIQUE ----------#
                        final_outcomes['UTIL'] = np.where((final_outcomes['UTIL'] == 0) 
                                                          & (final_outcomes['PG'] != final_outcomes['Player']) 
                                                          & (final_outcomes['SG'] != final_outcomes['Player'])
                                                          & (final_outcomes['SF'] != final_outcomes['Player'])
                                                          & (final_outcomes['PF'] != final_outcomes['Player'])
                                                          & (final_outcomes['C'] != final_outcomes['Player'])
                                                          & (final_outcomes['G'] != final_outcomes['Player'])
                                                          & (final_outcomes['F'] != final_outcomes['Player'])
                                                          , final_outcomes['Player'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['UTIL'] == 0)
                                                          & (final_outcomes['PG'] != final_outcomes['Player.1']) 
                                                          & (final_outcomes['SG'] != final_outcomes['Player.1'])
                                                          & (final_outcomes['SF'] != final_outcomes['Player.1'])
                                                          & (final_outcomes['PF'] != final_outcomes['Player.1'])
                                                          & (final_outcomes['C'] != final_outcomes['Player.1'])
                                                          & (final_outcomes['G'] != final_outcomes['Player.1'])
                                                          & (final_outcomes['F'] != final_outcomes['Player.1'])
                                                          , final_outcomes['Player.1'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['UTIL'] == 0)
                                                          & (final_outcomes['PG'] != final_outcomes['Player.2']) 
                                                          & (final_outcomes['SG'] != final_outcomes['Player.2'])
                                                          & (final_outcomes['SF'] != final_outcomes['Player.2'])
                                                          & (final_outcomes['PF'] != final_outcomes['Player.2'])
                                                          & (final_outcomes['C'] != final_outcomes['Player.2'])
                                                          & (final_outcomes['G'] != final_outcomes['Player.2'])
                                                          & (final_outcomes['F'] != final_outcomes['Player.2'])
                                                          , final_outcomes['Player.2'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['UTIL'] == 0)
                                                          & (final_outcomes['PG'] != final_outcomes['Player.3']) 
                                                          & (final_outcomes['SG'] != final_outcomes['Player.3'])
                                                          & (final_outcomes['SF'] != final_outcomes['Player.3'])
                                                          & (final_outcomes['PF'] != final_outcomes['Player.3'])
                                                          & (final_outcomes['C'] != final_outcomes['Player.3'])
                                                          & (final_outcomes['G'] != final_outcomes['Player.3'])
                                                          & (final_outcomes['F'] != final_outcomes['Player.3'])
                                                          , final_outcomes['Player.3'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['UTIL'] == 0)
                                                          & (final_outcomes['PG'] != final_outcomes['Player.4']) 
                                                          & (final_outcomes['SG'] != final_outcomes['Player.4'])
                                                          & (final_outcomes['SF'] != final_outcomes['Player.4'])
                                                          & (final_outcomes['PF'] != final_outcomes['Player.4'])
                                                          & (final_outcomes['C'] != final_outcomes['Player.4'])
                                                          & (final_outcomes['G'] != final_outcomes['Player.4'])
                                                          & (final_outcomes['F'] != final_outcomes['Player.4'])
                                                          , final_outcomes['Player.4'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['UTIL'] == 0)
                                                          & (final_outcomes['PG'] != final_outcomes['Player.5']) 
                                                          & (final_outcomes['SG'] != final_outcomes['Player.5'])
                                                          & (final_outcomes['SF'] != final_outcomes['Player.5'])
                                                          & (final_outcomes['PF'] != final_outcomes['Player.5'])
                                                          & (final_outcomes['C'] != final_outcomes['Player.5'])
                                                          & (final_outcomes['G'] != final_outcomes['Player.5'])
                                                          & (final_outcomes['F'] != final_outcomes['Player.5'])
                                                          , final_outcomes['Player.5'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['UTIL'] == 0)
                                                          & (final_outcomes['PG'] != final_outcomes['Player.6']) 
                                                          & (final_outcomes['SG'] != final_outcomes['Player.6'])
                                                          & (final_outcomes['SF'] != final_outcomes['Player.6'])
                                                          & (final_outcomes['PF'] != final_outcomes['Player.6'])
                                                          & (final_outcomes['C'] != final_outcomes['Player.6'])
                                                          & (final_outcomes['G'] != final_outcomes['Player.6'])
                                                          & (final_outcomes['F'] != final_outcomes['Player.6'])
                                                          , final_outcomes['Player.6'], final_outcomes['UTIL'])
                        final_outcomes['UTIL'] = np.where((final_outcomes['UTIL'] == 0)
                                                          & (final_outcomes['PG'] != final_outcomes['Player.7']) 
                                                          & (final_outcomes['SG'] != final_outcomes['Player.7'])
                                                          & (final_outcomes['SF'] != final_outcomes['Player.7'])
                                                          & (final_outcomes['PF'] != final_outcomes['Player.7'])
                                                          & (final_outcomes['C'] != final_outcomes['Player.7'])
                                                          & (final_outcomes['G'] != final_outcomes['Player.7'])
                                                          & (final_outcomes['F'] != final_outcomes['Player.7'])
                                                          , final_outcomes['Player.7'], final_outcomes['UTIL'])
                        final_outcomes = final_outcomes.loc[final_outcomes['two_c'] <= 2]
                        final_sorted_outcomes = final_outcomes[['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'UTIL']]
                        final_sorted_outcomes.rename(columns={"PG": "Player", "SG": "Player.1", "SF": "Player.2", "PF": "Player.3", "C": "Player.4", "G": "Player.5", "F": "Player.6", "UTIL": "Player.7"}, inplace = True)
                        final_sorted_outcomes['Salary'] = sum([final_sorted_outcomes['Player'].map(salary_dict),
                                final_sorted_outcomes['Player.1'].map(salary_dict),
                                final_sorted_outcomes['Player.2'].map(salary_dict),
                                final_sorted_outcomes['Player.3'].map(salary_dict),
                                final_sorted_outcomes['Player.4'].map(salary_dict),
                                final_sorted_outcomes['Player.5'].map(salary_dict),
                                final_sorted_outcomes['Player.6'].map(salary_dict),
                                final_sorted_outcomes['Player.7'].map(salary_dict)])
                        final_sorted_outcomes['Proj'] = sum([final_sorted_outcomes['Player'].map(player_proj_dict),
                                final_sorted_outcomes['Player.1'].map(player_proj_dict),
                                final_sorted_outcomes['Player.2'].map(player_proj_dict),
                                final_sorted_outcomes['Player.3'].map(player_proj_dict),
                                final_sorted_outcomes['Player.4'].map(player_proj_dict),
                                final_sorted_outcomes['Player.5'].map(player_proj_dict),
                                final_sorted_outcomes['Player.6'].map(player_proj_dict),
                                final_sorted_outcomes['Player.7'].map(player_proj_dict)])
                        final_sorted_outcomes['Proj Own%'] = sum([final_sorted_outcomes['Player'].map(player_own_dict),
                                final_sorted_outcomes['Player.1'].map(player_own_dict),
                                final_sorted_outcomes['Player.2'].map(player_own_dict),
                                final_sorted_outcomes['Player.3'].map(player_own_dict),
                                final_sorted_outcomes['Player.4'].map(player_own_dict),
                                final_sorted_outcomes['Player.5'].map(player_own_dict),
                                final_sorted_outcomes['Player.6'].map(player_own_dict),
                                final_sorted_outcomes['Player.7'].map(player_own_dict)])
                        sort_df = final_sorted_outcomes.sort_values(by='Proj', ascending=False)
                        sort_df = sort_df.reset_index()
                        sort_df = sort_df.drop(['index'], axis=1)
                        display_frame = sort_df.apply(pd.to_numeric, errors='ignore')
                        display_frame = display_frame.drop_duplicates(subset=['Proj'])
                        display_frame = display_frame.round(2)

                with display_container:        
                    st.dataframe(data=display_frame, use_container_width = True)
                with hold_container:
                    hold_container = st.empty()
