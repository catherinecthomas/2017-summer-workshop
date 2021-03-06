from pandas import DataFrame, concat, read_pickle, Series, merge
from pandas.io.excel import read_excel
from numpy import isnan, isreal, repeat, shape
from scipy.stats import zscore
import sys, cPickle,os
import random, urllib2

CENSUS_YEAR = 2012

# SF1 variable definitions
# https://api.census.gov/data/2010/sf1/variables.html
# ACS variable definitions (big!)
# https://api.census.gov/data/2012/acs5/variables.html

#GET A CENSUS API KEY HERE: http://api.census.gov/data/key_signup.html
CENSUS_KEY = 'no_key' 

def extractListFromURL(data_source, variable, year):
    if(data_source=='sf1'):
        url = 'http://api.census.gov/data/2010/sf1?key='+CENSUS_KEY+'&get=' + variable + '&in=state:36&for=zip+code+tabulation+area'
    elif(data_source=='acs5'):
        url = 'http://api.census.gov/data/'+str(year)+ '/acs5?key='+CENSUS_KEY+'&get=' + variable + '&for=zip+code+tabulation+area:*'

    print 'collecting data from:', url
        
    response = urllib2.urlopen(url)
    resp_text = response.read().split('\n') 
    if(data_source=='sf1'):
        data = map(lambda x:map(int, x.replace(']', '').replace('[', '').replace('"','').split(',')[0:3]), resp_text[1:])
    elif(data_source=='acs5'):
        resp_text = filter(lambda x: 'null' not in x, resp_text)
        data = map(lambda x:map(int, x.replace(']', '').replace('[', '').replace('"','').split(',')[0:2]), resp_text[1:])
    return data

zip_locs = DataFrame.from_csv('data/zip_names.csv',index_col='ZIP')
all_zips = zip_locs.index.tolist()

if(CENSUS_KEY=='no_key'):
    print 'no census API key found, get one here: http://api.census.gov/data/key_signup.html'
    raise SystemExit

demographics = DataFrame(columns=['ZIP', 'population'])
for data_line in extractListFromURL('sf1', 'PCT0130001', CENSUS_YEAR): #TOTAL POPULATION   P0010001 #POPULATION IN HOUSEHOUDS PCT0130001
    [population, junk, zip] = data_line
    if(zip in all_zips): demographics = demographics.append({'ZIP':zip, 'population':population}, ignore_index=True)
demographics.index = map(int, demographics['ZIP'])

SF1_KEYS = {'male':['PCT0130003', 'PCT0130004', 'PCT0130005', 'PCT0130006'],
            'female':['PCT0130027', 'PCT0130028', 'PCT0130029', 'PCT0130030']}
demographics['population_over_18'] = demographics['population']
for sex in ['female', 'male']:
    for sf1_var in SF1_KEYS[sex]:
        for data_line in extractListFromURL('sf1', sf1_var,CENSUS_YEAR):
            [population, junk, zip] = data_line
            if(zip in all_zips):
                demographics.loc[demographics.ZIP==zip, 'population_over_18'] = demographics.ix[zip]['population_over_18'] - population

demographics['income'] = Series(repeat(0, shape(demographics)[0]), index=demographics.index)
for data_line in extractListFromURL('acs5', 'B19301_001E',CENSUS_YEAR):
    [income, zip] = data_line
    demographics.loc[demographics.ZIP==zip, 'income'] =income

demographics['z_income'] = zscore(demographics.income)

demographics['mbsa'] = Series(repeat(0, shape(demographics)[0]), index=demographics.index)
for data_line in extractListFromURL('acs5', 'C24020_003E',CENSUS_YEAR):
    [male_mbsa, zip] = data_line
    if(zip in all_zips): demographics.loc[demographics.ZIP==zip, 'mbsa'] = male_mbsa


for data_line in extractListFromURL('acs5', 'C24020_039E',CENSUS_YEAR):
    [female_mbsa, zip] = data_line
    if(zip in all_zips): demographics.loc[demographics.ZIP==zip, 'mbsa'] = demographics.ix[zip]['mbsa'] + female_mbsa

demographics['mbsa'] = demographics['mbsa']/ map(float, demographics['population'])

ACS_KEYS = {'male':['B23001_007E', 'B23001_014E', 'B23001_021E', 'B23001_028E', 'B23001_028E', 'B23001_035E', 'B23001_042E', 'B23001_049E',
                    'B23001_056E', 'B23001_063E', 'B23001_070E', 'B23001_075E', 'B23001_080E','B23001_085E'],
            'female':['B23001_093E','B23001_100E','B23001_107E','B23001_114E','B23001_121E','B23001_128E','B23001_135E',
                      'B23001_142E','B23001_149E','B23001_156E','B23001_161E','B23001_166E','B23001_171E']}

zip_workforce_size = {}
for sex in ['female', 'male']:
    for acs_var in ACS_KEYS[sex]:
        for data_line in extractListFromURL('acs5', acs_var,CENSUS_YEAR):
            [value, zip] = data_line
            if(zip in all_zips): 
                if(not zip_workforce_size.has_key(zip)):  zip_workforce_size[zip] = int(value)
                else: zip_workforce_size[zip] +=  int(value)


demographics['workforce'] = Series(repeat(0, shape(demographics)[0]), index=demographics.index)
for zip, workforce_size in zip_workforce_size.iteritems():
    try:
        demographics.loc[demographics.ZIP==zip, 'workforce'] = workforce_size/float(demographics.ix[zip]['population'])
    except ZeroDivisionError:
        print 'bad population:', zip

demographics['mbsa_workforce'] = demographics['mbsa'] / demographics['workforce']
demographics['z_mbsa_workforce'] = zscore(demographics['mbsa_workforce'])

ACS_KEYS = {'female':{'ns':'B15002_020E', 'n4': 'B15002_021E', '5+6':'B15002_022E', '7+8':'B15002_023E',
                      '9':'B15002_024E', '10':'B15002_024E', '11':'B15002_025E', '12':'B15002_026E', 
                      'hs':'B15002_028E', 'sc1':'B15002_029E', 'sc2':'B15002_030E',
                      'aa':'B15002_031E', 'ba':'B15002_032E', 'ma':'B15002_033E', 
                      'pro':'B15002_034E','phd':'B15002_035E'},
            'male': {'ns':'B15002_003E', 'n4': 'B15002_004E', '5+6':'B15002_005E', '7+8':'B15002_006E',
                     '9':'B15002_007E', '10':'B15002_008E', '11':'B15002_009E', '12':'B15002_010E',
                     'hs':'B15002_011E', 'sc1':'B15002_012E', 'sc2':'B15002_013E',
                     'aa':'B15002_014E', 'ba':'B15002_015E', 'ma':'B15002_016E',
                     'pro':'B15002_017E', 'phd':'B15002_018E'} }
zip_ed = {}
for sex in ['female', 'male']:
    for ed_key, acs_var in ACS_KEYS[sex].iteritems():
        for data_line in extractListFromURL('acs5', acs_var, CENSUS_YEAR):
            [value, zip] = data_line
            if(int(zip) in all_zips):   
                if(not zip_ed.has_key(int(zip))):  zip_ed[int(zip)] = {sex+'_'+ed_key : int(value)}
                else: zip_ed[int(zip)][sex+'_'+ed_key] = int(value)

zip_ed_df = DataFrame(columns = ['ZIP'] + ACS_KEYS['female'].keys())
for zip in all_zips:
    zip_total = {'ZIP':zip}
    for ed_key in ACS_KEYS['female'].keys():
        try:
            zip_total[ed_key] = (zip_ed[zip]['male_'+ed_key]+ zip_ed[zip]['female_'+ed_key]) / float(demographics.ix[zip]['population'])
        except ZeroDivisionError:
            print 'bad ZIP population:', zip
    zip_ed_df = zip_ed_df.append( zip_total , ignore_index=True)
zip_ed_df.index = map(int, zip_ed_df.ZIP)

demographics = merge(zip_ed_df, demographics, on='ZIP')
demographics.index = map(int, demographics.ZIP)

demographics['education'] = (2.5*demographics['n4'] + 5.5*demographics['5+6'] + 7.5*demographics['7+8'] + 9*demographics['9'] + 10*demographics['10'] + 11*demographics['11'] + 12*demographics['12'] + 12*demographics['hs'] +13*demographics['sc1'] + 13*demographics['sc2'] +  14*demographics['aa'] + 16*demographics['ba'] + 18*demographics['ma'] + 18*demographics['pro'] + 18*demographics['phd']) 

demographics['z_education'] = zscore(demographics['education'])

demographics['ses'] = demographics['z_mbsa_workforce'] + demographics['z_income'] + demographics['z_education']

demographics['desc'] = Series(repeat(0, shape(demographics)[0]), index=demographics.index)
for zip in demographics.ZIP: 
    demographics.loc[demographics.ZIP==zip,'desc']= zip_locs.ix[int(zip)][0] + ':' + zip_locs.ix[int(zip)][1]

demographics['ZIP'] = demographics.index
demographics['desc'] = Series(repeat(0, shape(demographics)[0]), index=demographics.index)
for zip in demographics.ZIP: 
    demographics.loc[demographics.ZIP==zip,'desc']= zip_locs.ix[int(zip)][0] + ':' + zip_locs.ix[int(zip)][1]

cPickle.dump(demographics, open('data/demographics.dat', 'wb'),1)

