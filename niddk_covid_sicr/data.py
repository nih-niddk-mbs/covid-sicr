"""Functions for getting data needed to fit the models."""

import bs4
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm
from typing import Union
from urllib.error import HTTPError
import urllib.request, json
import os
from datetime import timedelta, date
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'

JHU_FILTER_DEFAULTS = {'confirmed': 5, 'recovered': 1, 'deaths': 0}
COVIDTRACKER_FILTER_DEFAULTS = {'cum_cases': 5, 'cum_recover': 1, 'cum_deaths': 0}

US_STATE_ABBREV = {
    'Alabama': 'US_AL',
    'Alaska': 'US_AK',
    'American Samoa': 'US_AS',
    'Arizona': 'US_AZ',
    'Arkansas': 'US_AR',
    'California': 'US_CA',
    'Colorado': 'US_CO',
    'Connecticut': 'US_CT',
    'Delaware': 'US_DE',
    'District of Columbia': 'US_DC',
    'Florida': 'US_FL',
    'Georgia': 'US_GA',
    'Guam': 'US_GU',
    'Hawaii': 'US_HI',
    'Idaho': 'US_ID',
    'Illinois': 'US_IL',
    'Indiana': 'US_IN',
    'Iowa': 'US_IA',
    'Kansas': 'US_KS',
    'Kentucky': 'US_KY',
    'Louisiana': 'US_LA',
    'Maine': 'US_ME',
    'Maryland': 'US_MD',
    'Massachusetts': 'US_MA',
    'Michigan': 'US_MI',
    'Minnesota': 'US_MN',
    'Mississippi': 'US_MS',
    'Missouri': 'US_MO',
    'Montana': 'US_MT',
    'Nebraska': 'US_NE',
    'Nevada': 'US_NV',
    'New Hampshire': 'US_NH',
    'New Jersey': 'US_NJ',
    'New Mexico': 'US_NM',
    'New York': 'US_NY',
    'North Carolina': 'US_NC',
    'North Dakota': 'US_ND',
    'Northern Mariana Islands':'US_MP',
    'Ohio': 'US_OH',
    'Oklahoma': 'US_OK',
    'Oregon': 'US_OR',
    'Pennsylvania': 'US_PA',
    'Puerto Rico': 'US_PR',
    'Rhode Island': 'US_RI',
    'South Carolina': 'US_SC',
    'South Dakota': 'US_SD',
    'Tennessee': 'US_TN',
    'Texas': 'US_TX',
    'Utah': 'US_UT',
    'Vermont': 'US_VT',
    'Virgin Islands': 'US_VI',
    'Virginia': 'US_VA',
    'Washington': 'US_WA',
    'West Virginia': 'US_WV',
    'Wisconsin': 'US_WI',
    'Wyoming': 'US_WY'
}

def get_jhu(data_path: str, filter_: Union[dict, bool] = True) -> None:
    """Gets data from Johns Hopkins CSSEGIS (countries only).

    https://coronavirus.jhu.edu/map.html
    https://github.com/CSSEGISandData/COVID-19

    Args:
        data_path (str): Full path to data directory.

    Returns:
        None
    """
    # Where JHU stores their data
    url_template = ("https://raw.githubusercontent.com/CSSEGISandData/"
                    "COVID-19/master/csse_covid_19_data/"
                    "csse_covid_19_time_series/time_series_covid19_%s_%s.csv")

    # Scrape the data
    dfs = {}
    for region in ['global', 'US']:
        dfs[region] = {}
        for kind in ['confirmed', 'deaths', 'recovered']:
            url = url_template % (kind, region)  # Create the full data URL
            try:
                df = pd.read_csv(url)  # Download the data into a dataframe
            except HTTPError:
                print("Could not download data for %s, %s" % (kind, region))
            else:
                if region == 'global':
                    has_no_province = df['Province/State'].isnull()
                    # Whole countries only; use country name as index
                    df1 = df[has_no_province].set_index('Country/Region')
                    more_dfs = []
                    for country in ['China', 'Canada', 'Australia']:
                        if country == 'Canada' and kind in 'recovered':
                            continue
                        is_c = df['Country/Region'] == country
                        df2 = df[is_c].sum(axis=0, skipna=False).to_frame().T
                        df2['Country/Region'] = country
                        df2 = df2.set_index('Country/Region')
                        more_dfs.append(df2)
                    df = pd.concat([df1] + more_dfs)
                elif region == 'US':
                    # Use state name as index
                    # for k, v in US_STATE_ABBREV.items(): # get US state abbrev
                    #     if not US_STATE_ABBREV[k].startswith('US_'):
                    #         US_STATE_ABBREV[k] = 'US_' + v # Add 'US_' to abbrev
                    df.replace(US_STATE_ABBREV, inplace=True)
                    df = df.set_index('Province_State')
                    df = df.groupby('Province_State').sum() # combine counties to create state level data

                df = df[[x for x in df if any(year in x for year in ['20', '21'])]]  # Use only data columns
                                                # 20 or 21 signifies 2020 or 2021
                dfs[region][kind] = df  # Add to dictionary of dataframes

    # Generate a list of countries that have "good" data,
    # according to these criteria:
    good_countries = get_countries(dfs['global'], filter_=filter_)
    # For each "good" country,
    # reformat and save that data in its own .csv file.
    source = dfs['global']
    for country in tqdm(good_countries, desc='Countries'):  # For each country
        if country in ['Diamond Princess', 'Grand Princess', 'MS Zaandam', 'Samoa',
                       'Vanuatu', 'Marshall Islands', 'US', 'Micronesia','Kiribati']:
            print("Skipping {}".format(country))
            continue
        # If we have data in the downloaded JHU files for that country
        if country in source['confirmed'].index:
            df = pd.DataFrame(columns=['dates2', 'cum_cases', 'cum_deaths',
                                       'cum_recover', 'new_cases',
                                       'new_deaths', 'new_recover',
                                       'new_uninfected'])
            df['dates2'] = source['confirmed'].columns
            df['dates2'] = df['dates2'].apply(fix_jhu_dates)
            df['cum_cases'] = source['confirmed'].loc[country].values
            df['cum_deaths'] = source['deaths'].loc[country].values
            df['cum_recover'] = source['recovered'].loc[country].values
            df[['new_cases', 'new_deaths', 'new_recover']] = \
                df[['cum_cases', 'cum_deaths', 'cum_recover']].diff()
            df['new_uninfected'] = df['new_recover'] + df['new_deaths']


            try:
                population = get_population_count(data_path, country)
                df['population'] = population
            except:
                pass

            # Fill NaN with 0 and convert to int
            dfs[country] = df.set_index('dates2').fillna(0).astype(int)
            dfs[country].to_csv(data_path / ('covidtimeseries_%s.csv' % country))

        else:
            print("No data for %s" % country)

    source = dfs['US']
    states = source['confirmed'].index.tolist()

    us_recovery_data = covid_tracking_recovery(data_path)
    for state in tqdm(states, desc='US States'):  # For each country
        if state in ['Diamond Princess', 'Grand Princess', 'MS Zaandam', 'US_AS']:
            print("Skipping {}".format(state))
            continue
        # If we have data in the downloaded JHU files for that country
        if state in source['confirmed'].index:
            df = pd.DataFrame(columns=['dates2', 'cum_cases', 'cum_deaths',
                                       'new_cases','new_deaths','new_uninfected'])
            df['dates2'] = source['confirmed'].columns
            df['dates2'] = df['dates2'].apply(fix_jhu_dates)
            df['cum_cases'] = source['confirmed'].loc[state].values
            df['cum_deaths'] = source['deaths'].loc[state].values

            df[['new_cases', 'new_deaths']] = df[['cum_cases', 'cum_deaths']].diff()

            # add recovery data
            df.set_index('dates2', inplace=True)
            df = df.merge(us_recovery_data[state], on='dates2', how='left')

            df['tmp_new_recover'] = df['new_recover'].fillna(0).astype(int) # create temp new recover for
            df['new_uninfected'] = df['tmp_new_recover'] + df['new_deaths'] # new uninfected calculation
            df = df.fillna(-1).astype(int)
            df = df.drop(['tmp_new_recover'], axis=1)

            try:
                population = get_population_count(data_path, state)
                df['population'] = population
            except:
                pass

            dfs[state] = df
            dfs[state].to_csv(data_path /
                                ('covidtimeseries_%s.csv' % state))
        else:
            print("No data for %s" % state)

def fix_jhu_dates(x):
    y = datetime.strptime(x, '%m/%d/%y')
    return datetime.strftime(y, '%m/%d/%y')


def fix_ct_dates(x):
    return datetime.strptime(str(x), '%Y%m%d')


def get_countries(d: pd.DataFrame, filter_: Union[dict, bool] = True):
    """Get a list of countries from a global dataframe optionally passing
    a quality check

    Args:
        d (pd.DataFrame): Data from JHU tracker (e.g. df['global]).
        filter (bool, optional): Whether to filter by quality criteria.
    """
    good = set(d['confirmed'].index)
    if filter_ and not isinstance(filter_, dict):
        filter_ = JHU_FILTER_DEFAULTS
    if filter_:
        for key, minimum in filter_.items():
            enough = d[key].index[d[key].max(axis=1) >= minimum].tolist()
            good = good.intersection(enough)
    bad = set(d['confirmed'].index).difference(good)
    # print("JHU data acceptable for %s" % ','.join(good))
    # print("JHU data not acceptable for %s" % ','.join(bad))
    return good

def get_population_count(data_path:str, roi):
    """ Check if we have population count for roi and
        add to timeseries df if we do.

        Args:
            data_path (str): Full path to data directory.
            roi (str): Region.
        Returns:
            population (int): Population count for ROI (if exists).
    """
    try:  # open population file
        df_pop = pd.read_csv(data_path / 'population_estimates.csv')
    except:
        print("Missing population_estimates.csv in data-path")

    try:
        population = df_pop.query('roi == "{}"'.format(roi))['population'].values
    except:
        print("{} population estimate not found in population_estimates.csv".format(args.roi))

    return int(population)

def covid_tracking_recovery(data_path: str):
    """Gets archived US recovery data from The COVID Tracking Project.
    https://covidtracking.com

    Args:
        data_path (str): Full path to data directory.

    Returns:
        ctp_dfs (dict): Dictionary containing US States (keys) and dataframes
        containing dates, recovery data (values).
    """
    archived_data = data_path / 'covid-tracking-project-recovery.csv'
    df_raw = pd.read_csv(archived_data)
    states = df_raw['state'].unique()
    ctp_dfs = {}
    for state in states: # For each country
        source = df_raw[df_raw['state'] == state] # Only the given state
        df = pd.DataFrame(columns=['dates2','cum_recover','new_recover'])
        df['dates2'] = source['date'].apply(fix_ct_dates) # Convert date format
        # first check if roi reports recovery data as recovered
        if source['recovered'].isnull().all() == False:
            df['cum_recover'] = source['recovered'].values
        # check if roi reports recovery data as hospitalizedDischarged
        elif source['hospitalizedDischarged'].isnull().all() == False:
            df['cum_recover'] = source['hospitalizedDischarged'].values
        else:
            df['cum_recover'] = np.NaN

        df.sort_values(by=['dates2'], inplace=True) # sort by datetime obj before converting to string
        df['dates2'] = pd.to_datetime(df['dates2']).dt.strftime('%m/%d/%y') # convert dates to string
        df = df.set_index('dates2') # Convert to int
        df['new_recover'] = df['cum_recover'].diff()
        ctp_dfs['US_'+state] = df
    return ctp_dfs


def get_canada(data_path: str, filter_: Union[dict, bool] = True,
                       fixes: bool = False) -> None:
    """ Gets data from Canada's Open Covid group for Canadian Provinces.
        https://opencovid.ca/
    """
    dfs = [] # we will append dfs for cases, deaths, recovered here
    # URL for API call to get Province-level timeseries data starting on Jan 22 2020
    url_template = 'https://api.opencovid.ca/timeseries?stat=%s&loc=prov&date=01-22-2020'
    for kind in ['cases', 'mortality', 'recovered']:
        url_path = url_template % kind  # Create the full data URL
        with urllib.request.urlopen(url_path) as url:
            data = json.loads(url.read().decode())
            source = pd.json_normalize(data[kind])
            if kind == 'cases':
                source.drop('cases', axis=1, inplace=True) # removing this column so
                # we can index into date on all 3 dfs at same position
            source.rename(columns={source.columns[1]: "date" }, inplace=True)
            dfs.append(source)
    cases = dfs[0]
    deaths = dfs[1]
    recovered = dfs[2]
    # combine dfs
    df_rawtemp = cases.merge(recovered, on=['date', 'province'], how='outer')
    df_raw = df_rawtemp.merge(deaths, on=['date', 'province'], how='outer')
    df_raw.fillna(0, inplace=True)

    provinces = ['Alberta', 'BC', 'Manitoba', 'New Brunswick', 'NL',
                'Nova Scotia', 'Nunavut', 'NWT', 'Ontario', 'PEI', 'Quebec',
                'Saskatchewan', 'Yukon']

    # Export timeseries data for each province
    for province in tqdm(provinces, desc='Canadian Provinces'):
        source = df_raw[df_raw['province'] == province]  # Only the given province
        df = pd.DataFrame(columns=['dates2','cum_cases', 'cum_deaths',
                                   'cum_recover', 'new_cases',
                                   'new_deaths', 'new_recover',
                                   'new_uninfected'])
        df['dates2'] = source['date'].apply(fix_canada_dates) # Convert date format
        df['cum_cases'] = source['cumulative_cases'].values
        df['cum_deaths'] = source['cumulative_deaths'].values
        df['cum_recover'] = source['cumulative_recovered'].values

        df[['new_cases', 'new_deaths', 'new_recover']] = \
            df[['cum_cases', 'cum_deaths', 'cum_recover']].diff()
        df['new_uninfected'] = df['new_recover'] + df['new_deaths']

        try:
            population = get_population_count(data_path, 'CA_' + province)
            df['population'] = population
        except:
            pass

        df.sort_values(by=['dates2'], inplace=True) # sort by datetime obj before converting to string
        df['dates2'] = pd.to_datetime(df['dates2']).dt.strftime('%m/%d/%y') # convert dates to string
        df = df.set_index('dates2').fillna(0).astype(int) # Fill NaN with 0 and convert to int
        df.to_csv(data_path / ('covidtimeseries_CA_%s.csv' % province))

def fix_canada_dates(x):
    return datetime.strptime(x, '%d-%m-%Y')

def get_brazil(data_path: str, filter_: Union[dict, bool] = True,
                       fixes: bool = False) -> None:
    """ Get state-level data for Brazil.

    https://github.com/wcota/covid19br (Wesley Cota)

    """

    url = "https://raw.githubusercontent.com/wcota/covid19br/master/cases-brazil-states.csv"
    try:
        df_raw = pd.read_csv(url)
    except HTTPError:
        print("Could not download state-level data for Brazil")

    state_code = {'AC':'Acre', 'AL':'Alagoas', 'AM':'Amazonas', 'AP':'Amapa',
                  'BA':'Bahia','CE':'Ceara', 'DF':'Distrito Federal',
                  'ES':'Espirito Santo', 'GO':'Goias', 'MA':'Maranhao',
                  'MG':'Minas Gerais', 'MS':'Mato Grosso do Sul', 'MT':'Mato Grosso',
                  'PA':'Para', 'PB':'Paraiba', 'PE':'Pernambuco', 'PI':'Piaui',
                  'PR':'Parana', 'RJ':'Rio de Janeiro', 'RN':'Rio Grande do Norte',
                  'RO':'Rondonia', 'RR':'Roraima', 'RS':'Rio Grande do Sul',
                  'SC':'Santa Catarina', 'SE':'Sergipe', 'SP':'Sao Paulo', 'TO':'Tocantins'}

    for state in tqdm(state_code, desc='Brazilian States'):
        source = df_raw[df_raw['state'] == state]  # Only the given province
        df = pd.DataFrame(columns=['dates2','cum_cases', 'cum_deaths',
                                   'cum_recover', 'new_cases',
                                   'new_deaths', 'new_recover',
                                   'new_uninfected'])

        df['dates2'] = source['date']
        df['cum_cases'] = source['totalCases'].values
        df['cum_deaths'] = source['deaths'].values
        df['cum_recover'] = source['recovered'].values
        df['new_cases'] = source['newCases'].values
        df['new_deaths'] = source['newDeaths'].values
        df['new_recover'] = df['cum_recover'].diff()
        df['new_uninfected'] = df['new_recover'] + df['new_deaths']

        try:
            roi = 'BR_' + state_code[state]
            population = get_population_count(data_path, roi)
            df['population'] = population
        except:
            print("Could not add population data for {}".format(state))
            pass

        df.sort_values(by=['dates2'], inplace=True) # sort by datetime obj before converting to string
        df['dates2'] = pd.to_datetime(df['dates2']).dt.strftime('%m/%d/%y') # convert dates to string
        df = df.set_index('dates2').fillna(0).astype(int) # Fill NaN with 0 and convert to int
        df.to_csv(data_path / ('covidtimeseries_BR_%s.csv' % state_code[state]))


def get_owid_tests(data_path: str, filter_: Union[dict, bool] = True,
                       fixes: bool = False) -> None:
    """ Get testing data from Our World In Data
        https://github.com/owid/covid-19-data
        Add columns cum_tests and new_tests to csvs in data_path. """
    url = 'https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/testing/covid-testing-all-observations.csv'
    src = pd.read_csv(url)
    roi_codes = pd.read_csv(data_path / 'country_iso_codes.csv')
    roi_codes_dict = pd.Series(roi_codes.Country.values,index=roi_codes['Alpha-3 code']).to_dict()
    # trim down source dataframe
    src_trim = pd.DataFrame(columns=['dates2','Alpha-3 code','cum_tests'])
    src_trim['dates2'] = src['Date'].apply(fix_owid_dates).values # fix dates
    src_trim['Alpha-3 code'] = src['ISO code'].values
    src_trim['cum_tests'] = src['Cumulative total'].fillna(-1).astype(int).values
    src_trim.set_index('dates2',inplace=True, drop=True)

    src_rois = src_trim['Alpha-3 code'].unique()
    unavailable_testing_data = [] # for appending rois that don't have testing data

    for roi in roi_codes_dict:
        if roi not in src_rois:
            unavailable_testing_data.append(roi)
            continue
        if roi_codes_dict[roi] in ["US", "Marshall Islands", "Micronesia", "Samoa", "Vanuatu"]: # skipping because bad data
            continue
        try:
            timeseries_path = data_path / ('covidtimeseries_%s.csv' % roi_codes_dict[roi])
            df_timeseries = pd.read_csv(timeseries_path, index_col='dates2')
        except FileNotFoundError as fnf_error:
            print(fnf_error, 'Could not add OWID data.')
            pass

        for i in df_timeseries.columns: # Check if OWID testng data already included
            if 'tests' in i:
                df_timeseries.drop([i], axis=1, inplace=True) # drop so we can add new
        src_roi = src_trim[src_trim['Alpha-3 code'] == roi] # filter rows that match roi

        df_combined = df_timeseries.merge(src_roi[['cum_tests']], how='left', on='dates2')
        df_combined['new_tests'] = df_combined['cum_tests'].diff()
        df_combined.loc[df_combined['new_tests'] < 0, 'new_tests'] = -1 # Handle cases where
        # cumulative counts decrease and new_tests becomes a large negative number

        df_combined[['cum_tests', 'new_tests']] = df_combined[['cum_tests', 'new_tests']].fillna(-1).astype(int).values
        df_combined = df_combined.loc[:, ~df_combined.columns.str.contains('^Unnamed')]
        df_combined.to_csv(timeseries_path) # overwrite timeseries CSV

    print("OWID global test results missing for: ")
    for roi in roi_codes_dict:
        if roi in unavailable_testing_data:
            print(roi_codes_dict[roi], end=" ")
    print("")

def get_owid_global_vaccines(data_path: str, filter_: Union[dict, bool] = True,
                       fixes: bool = False) -> None:
    """ Get global vaccines data from Our World In Data
        https://github.com/owid/covid-19-data
        Add columns to global csvs in data_path. """
    url = 'https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/vaccinations.csv'
    src = pd.read_csv(url)
    src_trim = pd.DataFrame(columns=['dates2', 'Alpha-3 code', 'cum_vaccinations', 'daily_vaccinations',
                                     'cum_people_vaccinated', 'cum_people_fully_vaccinated'])
    src_trim['dates2'] = src['date'].apply(fix_owid_dates).values # fix dates
    src_trim['Alpha-3 code'] = src['iso_code'].values
    src_trim['cum_vaccinations'] = src['total_vaccinations'].values
    src_trim['daily_vaccinations'] = src['daily_vaccinations'].values
    src_trim['cum_people_vaccinated'] = src['people_vaccinated'].values
    src_trim['cum_people_fully_vaccinated'] = src['people_fully_vaccinated'].values

    roi_codes = pd.read_csv(data_path / 'country_iso_codes.csv')
    roi_codes_dict = pd.Series(roi_codes.Country.values,index=roi_codes['Alpha-3 code']).to_dict()

    # trim down source dataframe
    src_trim.set_index('dates2',inplace=True, drop=True)

    src_rois = src_trim['Alpha-3 code'].unique()
    unavailable_testing_data = [] # for appending rois that don't have testing data

    for roi in roi_codes_dict:
        if roi not in src_rois:
            unavailable_testing_data.append(roi)
            continue
        if roi_codes_dict[roi] in ["US", "Marshall Islands", "Micronesia", "Samoa", "Vanuatu"]: # skipping because no data
            continue
        try:
            timeseries_path = data_path / ('covidtimeseries_%s.csv' % roi_codes_dict[roi])
            df_timeseries = pd.read_csv(timeseries_path, index_col='dates2')
        except FileNotFoundError as fnf_error:
            print(fnf_error, 'Could not add OWID global vaccines data.')
            pass

        for i in df_timeseries.columns: # Check if OWID testing data already included
            if 'vaccin' in i:
                df_timeseries.drop([i], axis=1, inplace=True) # drop so we can add new
        src_roi = src_trim[src_trim['Alpha-3 code'] == roi] # filter rows that match roi

        df_combined = df_timeseries.merge(src_roi[['cum_vaccinations', 'daily_vaccinations', 'cum_people_vaccinated',
                                                               'cum_people_fully_vaccinated']], how='left', on='dates2')
        cum_vacc_columns = ['vaccinations', 'people_vaccinated', 'people_fully_vaccinated']
        df = dummy_cumulative_new_counts(roi_codes_dict[roi], df_combined, cum_vacc_columns)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.to_csv(timeseries_path) # overwrite timeseries CSV


    print("OWID global vaccine results missing for: ")
    for roi in roi_codes_dict:
        if roi in unavailable_testing_data:
            print(roi_codes_dict[roi], end=" ")
    print("")

def dummy_cumulative_new_counts(roi, df, columns: list):
    """ There are cases where cum counts go missing and new counts get missed.
        New counts spike when cumulative counts go to -1 for missing data and
        the difference is taken between a new cumulative count and -1.
        We don't want it to spike, and we don't want to miss new counts before the gap.
        So create a dummy dataframe with forward filled cumulative counts and
        perform new cases calculation, then merge those new cases back into dataframe.

        Args:
            roi (str): Region we are working with; used for print statements.
            df (pd.DataFrame): DataFrame containing counts but not new counts.
            columns (list): List of columns (without cum_ prefix) so create new counts for.

        Returns:
            df_fixed (pd.DataFrame): DataFrame containing cumulative and now new counts. """
    dfs = []
    df_tmp = df.copy()
    df_tmp.reset_index(inplace=True)
    for col in columns:
        cum_col = 'cum_' + col
        dummy_cum_col = 'dummy_' + cum_col
        new_col = 'new_' + col
        try:
            start = df_tmp[df_tmp[cum_col] > 0].index.values[0]
            df_ffill = df_tmp.iloc[start:]
            df_ffill.set_index('dates2', drop=True, inplace=True)
            df_ffill[dummy_cum_col] = df_ffill[cum_col].ffill().astype(int).values
            df_ffill[new_col] = df_ffill[dummy_cum_col].diff().astype('Int64')
            # If cumulative counts are missing, set new counts to -1 so they don't become 0.
            df_ffill.loc[df_ffill[cum_col].isnull(), new_col] = -1
        except:
            print(f'No {cum_col} data to add for {roi}.')
            df_ffill[new_col] = -1
        df_ffill = df_ffill[~df_ffill.index.duplicated()] # fix duplication issue
        dfs.append(df_ffill[new_col])

    df_new = pd.concat(dfs, axis=1)
    df_new = df_new.fillna(-1).astype(int)
    df_fixed = df.join(df_new)
    df_fixed = df_fixed.fillna(-1).astype(int)
    return df_fixed

def get_owid_us_vaccines(data_path: str, filter_: Union[dict, bool] = True,
                       fixes: bool = False) -> None:
    """ Get US vaccines data from Our World In Data
        https://github.com/owid/covid-19-data
        Add columns to US csvs in data_path. """

    url = 'https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/us_state_vaccinations.csv'
    src = pd.read_csv(url)
    src_trim = pd.DataFrame(columns=['dates2', 'region', 'cum_vaccinations', 'daily_vaccinations',
                                     'people_vaccinated', 'people_fully_vaccinated'])

    src_trim['dates2'] = src['date'].apply(fix_owid_dates).values # fix dates
    src_trim['region'] = src['location'].values
    src_trim['cum_vaccinations'] = src['total_vaccinations'].values
    src_trim['daily_vaccinations'] = src['daily_vaccinations'].values
    src_trim['cum_people_vaccinated'] = src['people_vaccinated'].values
    src_trim['cum_people_fully_vaccinated'] = src['people_fully_vaccinated'].values
    src_trim.set_index('dates2', inplace=True, drop=True)
    src_trim.replace("New York State", "New York", inplace=True) # fix NY name
    src_rois = src_trim['region'].unique()
    for roi in src_rois:
        if roi in US_STATE_ABBREV:
            try:
                timeseries_path = data_path / ('covidtimeseries_%s.csv' % US_STATE_ABBREV[roi])
                df_timeseries = pd.read_csv(timeseries_path, index_col='dates2')

            except FileNotFoundError as fnf_error:
                print(fnf_error, 'Could not add OWID vaccinations data.')
                pass

            for i in df_timeseries.columns: # Check if OWID vaccines data already included
                if 'vaccin' in i:
                    df_timeseries.drop([i], axis=1, inplace=True) # drop so we can add new

            src_roi = src_trim[src_trim['region'] == roi] # filter rows that match roi

            df_combined = df_timeseries.merge(src_roi[['cum_vaccinations', 'daily_vaccinations', 'cum_people_vaccinated',
                                                       'cum_people_fully_vaccinated']], how='left', on='dates2')

            cum_vacc_columns = ['vaccinations', 'people_vaccinated', 'people_fully_vaccinated']
            df = dummy_cumulative_new_counts(US_STATE_ABBREV[roi], df_combined, cum_vacc_columns)

            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df.to_csv(timeseries_path) # overwrite timeseries CSV


def fix_owid_dates(x):
    y = datetime.strptime(x, '%Y-%m-%d')
    return datetime.strftime(y, '%m/%d/%y')


def get_jhu_us_states_tests(data_path: str, filter_: Union[dict, bool] = False) -> None:
    """ Scrape JHU for US State level test results. Data is stored as a collection of
        CSVs per date containing states and test results.

        Args:
            data_path (str): Full path to data directory.
        Returns:
            None
         """
    url_template = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports_us/%s.csv"
    # generate a list of dates for scraping
    start_dt = date(2020, 4, 12) # When JHU starts reporting
    end_dt = date.today()
    dates = []
    delta = end_dt - start_dt
    delta = delta.days
    for dt in daterange(start_dt, end_dt):
        dates.append(dt.strftime("%m-%d-%Y"))
    # cumulative tests are named 'People_Tested' for first 200 ish days
    # then cumulative tests are named 'Total_Test_Results' after 200 ish days
    dfs = []
    for i in tqdm(dates, desc=f'Scraping {delta} days of data across all states'):
        url = url_template % i
        try:
            df = pd.read_csv(url)
            df_trim = pd.DataFrame(columns=['Province_State', 'cum_tests', 'dates2'])
            df_trim['Province_State'] = df['Province_State'].values
            df_trim['dates2'] = fix_jhu_testing_dates(i)

            # handle cases where column is people_tested and then switches to Total_Test_Results
            if 'People_Tested' in df.columns:
                df_trim['cum_tests'] = df['People_Tested'].fillna(-1).astype(int).values
                dfs.append(df_trim)
            if 'Total_Test_Results' in df.columns:
                df_trim['cum_tests'] = df['Total_Test_Results'].fillna(-1).astype(int).values
                dfs.append(df_trim)
        except HTTPError:
            print("Could not download tests data for %s" % i)
    df_combined = pd.concat(dfs)
    df_combined.sort_values(by='Province_State', inplace=True)
    df_combined['Date'] = pd.to_datetime(df_combined['dates2'])
    rois = df_combined['Province_State'].unique()
    sorted_dfs = []
    for roi in rois:
        df_roi = df_combined[df_combined['Province_State'] == roi]
        df_roi = df_roi.sort_values(by="Date")
        df_roi['new_tests'] = df_roi['cum_tests'].diff().fillna(-1).astype(int)
        sorted_dfs.append(df_roi)

    df_tests = pd.concat(sorted_dfs)
    df_tests.reset_index(inplace=True, drop=True)
    df_tests.replace(US_STATE_ABBREV, inplace=True)
    df_tests.rename(columns={'Province_State': 'roi'}, inplace=True)

    # now open csvs in data_path that match rois and merge on csv to add cum_test and new_tests
    rois = df_tests.roi.unique().tolist()
    to_remove = ['Diamond Princess', 'Grand Princess', 'Recovered']
    for i in to_remove:
        if i in rois:
            rois.remove(i)

    for roi in rois:
        csv_path = data_path / f'covidtimeseries_{roi}.csv'
        try:
            df_timeseries = pd.read_csv(csv_path)
        except:
            print(f"{csv_path} not found in data path.")
        try:
            for i in df_timeseries.columns: # Check if testng data already included
                if 'tests' in i:
                    df_timeseries.drop([i], axis=1, inplace=True) # drop so we can add new
            df_roi_tests = df_tests[df_tests['roi'] == roi] # filter down to roi
            df_result = df_timeseries.merge(df_roi_tests, on='dates2', how='left')
            df_result.fillna(-1, inplace=True)
            df_result.loc[df_result['new_tests'] < 0, 'new_tests'] = -1 # Handle cases where
                        # cumulative counts decrease and new_tests becomes a large negative number
            df_result['new_tests'] = df_result['new_tests'].astype(int)
            df_result[['cum_tests', 'new_tests']] = df_result[['cum_tests', 'new_tests']].astype(int)
            df_result_trim = df_result[['dates2', 'cum_cases', 'new_cases',
                                        'cum_deaths', 'new_deaths', 'cum_recover',
                                        'new_recover', 'new_uninfected', 'cum_tests',
                                        'new_tests', 'population']].copy()

            df_result_trim = df_result_trim.loc[:, ~df_result_trim.columns.str.contains('^Unnamed')]
            df_result_trim.to_csv(csv_path) # overwrite timeseries CSV

        except:
            print(f'Could not get tests data for {roi}.')


def daterange(date1, date2):
    for n in range(int ((date2 - date1).days)+1):
        yield date1 + timedelta(n)

def fix_jhu_testing_dates(x):
    y = datetime.strptime(x, '%m-%d-%Y')
    return datetime.strftime(y, '%m/%d/%y')

def fix_negatives(data_path: str, plot: bool = False) -> None:
    """Fix negative values in daily data.

    The purpose of this script is to fix spurious negative values in new daily
    numbers.  For example, the cumulative total of cases should not go from N
    to a value less than N on a subsequent day.  This script fixes this by
    nulling such data and applying a monotonic spline interpolation in between
    valid days of data.  This only affects a small number of regions.  It
    overwrites the original .csv files produced by the functions above.

    Args:
        data_path (str): Full path to data directory.
        plot (bool): Whether to plot the changes.

    Returns:
        None
    """
    csvs = [x for x in data_path.iterdir() if 'covidtimeseries' in str(x)]
    for csv in tqdm(csvs, desc="Regions"):
        roi = str(csv).split('.')[0].split('_')[-1]
        df = pd.read_csv(csv)
        # Exclude final day because it is often a partial count.
        df = df.iloc[:-1]
        df = fix_neg(df, roi, plot=plot)
        df.to_csv(data_path / (csv.name.split('.')[0]+'.csv'))


def fix_neg(df: pd.DataFrame, roi: str,
            columns: list = ['cases', 'deaths', 'recover'],
            plot: bool = False) -> pd.DataFrame:
    """Used by `fix_negatives` to fix negatives values for a single region.

    This function uses monotonic spline interpolation to make sure that
    cumulative counts are non-decreasing.

    Args:
        df (pd.DataFrame): DataFrame containing data for one region.
        roi (str): One region, e.g 'US_MI' or 'Greece'.
        columns (list, optional): Columns to make non-decreasing.
            Defaults to ['cases', 'deaths', 'recover'].
    Returns:
        pd.DataFrame: [description]
    """
    for c in columns:
        cum = 'cum_%s' % c
        new = 'new_%s' % c
        before = df[cum].copy()
        non_zeros = df[df[new] > 0].index
        has_negs = before.diff().min() < 0
        if len(non_zeros) and has_negs:
            first_non_zero = non_zeros[0]
            maxx = df.loc[first_non_zero, cum].max()
            # Find the bad entries and null the corresponding
            # cumulative column, which are:
            # 1) Cumulative columns which are zero after previously
            # being non-zero
            bad = df.loc[first_non_zero:, cum] == 0
            df.loc[bad[bad].index, cum] = None
            # 2) New daily columns which are negative
            bad = df.loc[first_non_zero:, new] < 0
            df.loc[bad[bad].index, cum] = None
            # Protect against 0 null final value which screws up interpolator
            if np.isnan(df.loc[df.index[-1], cum]):
                df.loc[df.index[-1], cum] = maxx
            # Then run a loop which:
            while True:
                # Interpolates the cumulative column nulls to have
                # monotonic growth
                after = df[cum].interpolate('pchip')
                diff = after.diff()
                if diff.min() < 0:
                    # If there are still negative first-differences at this
                    # point, increase the corresponding cumulative values by 1.
                    neg_index = diff[diff < 0].index
                    df.loc[neg_index, cum] += 1
                else:
                    break
                # Then repeat
            if plot:
                plt.figure()
                plt.plot(df.index, before, label='raw')
                plt.plot(df.index, after, label='fixed')
                r = np.corrcoef(before, after)[0, 1]
                plt.title("%s %s Raw vs Fixed R=%.5g" % (roi, c, r))
                plt.legend()
        else:
            after = before
        # Make sure the first differences are now all non-negative
        assert after.diff().min() >= 0
        # Replace the values
        df[new] = df[cum].diff().fillna(0).astype(int).values
    return df


def negify_missing(data_path: str) -> None:
    """Fix negative values in daily data.

    The purpose of this script is to fix spurious negative values in new daily
    numbers.  For example, the cumulative total of cases should not go from N
    to a value less than N on a subsequent day.  This script fixes this by
    nulling such data and applying a monotonic spline interpolation in between
    valid days of data.  This only affects a small number of regions.  It
    overwrites the original .csv files produced by the functions above.

    Args:
        data_path (str): Full path to data directory.
        plot (bool): Whether to plot the changes.

    Returns:
        None
    """
    csvs = [x for x in data_path.iterdir() if 'covidtimeseries' in str(x)]
    for csv in tqdm(csvs, desc="Regions"):
        roi = str(csv).split('.')[0].split('_')[-1]
        df = pd.read_csv(csv)
        for kind in ['cases', 'deaths', 'recover']:
            if df['cum_%s' % kind].sum() == 0:
                print("Negifying 'new_%s' for %s" % (kind, roi))
                df['new_%s' % kind] = -1
        out = data_path / (csv.name.split('.')[0]+'.csv')
        df.to_csv(out)

def remove_old_rois(data_path: str):
    """Delete time-series files for regions no longer tracked, such as:
     Diamond Princess, MS Zaandam, Samoa, Vanuatu, Marshall Islands,
     US, US_AS (American Somoa)"""

    csvs = [x for x in data_path.iterdir() if 'covidtimeseries' in str(x)]
    rois_to_remove = ['Diamond Princess', 'Grand Princess', 'MS Zaandam', 'Samoa', 'Vanuatu',
                        'Marshall Islands', 'US', 'US_AS', 'Micronesia', 'Kiribati']
    for csv in csvs:
        roi = str(csv).split('.')[0].split('_', 1)[-1]
        if roi in rois_to_remove:
            try:
                if os.path.exists(csv):
                    print("Removing {} from data_path".format(roi))
                    os.remove(csv)
            except:
                print("could not remove {}. Check that path is correct.".format(csv))
