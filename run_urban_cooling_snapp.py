import os
import natcap.invest.urban_cooling_model

# Runnng the cooling Urban InVEST model
args = {
    'aoi_vector_path': os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'),
    # 'avg_rel_humidity': str(avg_humid),
    'biophysical_table_path': 'Biophysical Tables/biophysical_cooling_v03.csv',
    # 'building_vector_path': 'C:\\Users\\kibby\\OneDrive\\Desktop\\Research\\DOI\\Data\\Built '
    #                                                     'Infrastructure\\Microsoft\\urbans\\' + c + '.gpkg', 
    'cc_method': 'factors',
    'cc_weight_albedo': '',
    'cc_weight_eti': '',
    'cc_weight_shade': '',
    'do_energy_valuation': False,
    'do_productivity_valuation': False, # maybe true? need humidity if so 
    # 'energy_consumption_table_path': 'C:\\Users\\kibby\\OneDrive\\Desktop\\Research\\DOI\\Data\\Energy '
    #                                                     'Consumption '
    #                                                     'Table\\urban '
    #                                                     'tables\\' + c + '.csv',
    'green_area_cooling_distance': '50',
    'lulc_raster_path': re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), lulc_path),
    'n_workers': '-1',
    'ref_eto_raster_path': re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), raster_paths[0]),
    'results_suffix': c + '_' + year + '_' + month,
    't_air_average_radius': '600',
    't_ref': str(rural_ref_temp),
    'uhi_max': str(uhi),
    'workspace_dir': 'output/' + c,
    }
natcap.invest.urban_cooling_model.execute(args)