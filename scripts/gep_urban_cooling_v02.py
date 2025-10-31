# Libby Kula
#  Global GEP Urban Cooling
# 07/14/2025

import logging
import numpy as np
import os
import pygeoprocessing as pygeo
import pandas as pd
import geopandas as gpd
from osgeo import gdal
from osgeo import gdalconst
from osgeo import gdalnumeric
from osgeo import ogr
import matplotlib.pyplot as plt
import multiprocessing as mp
import hazelbean as hb
import ineqpy
import rasterio
from rasterio.mask import mask
import re 
import requests
import sys
import time
from scipy.stats import ttest_ind
import statsmodels.api as sm
import glob
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import shap
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score


# set wd
os.chdir("C:/Users/kibby/OneDrive/Desktop/Research/GEP")

temp_data = pd.read_csv('IEA CMCC/IEA-CMCC-WeatherForEnergy-Temperaturedaily-from-2019-01-to-2019-12.csv')
# temp_data = pd.read_csv('IEA CMCC/IEA-CMCC-WeatherForEnergy-Temperaturedailybypop-from-2019-01-to-2019-12.csv')

cdd_data = pd.read_csv('IEA CMCC/IEA-CMCC-WeatherForEnergy-CDDhum18dailybypop-from-2019-01-to-2019-12.csv') # do I want it with or without humidity?

temp_and_cdd_data = pd.merge(temp_data, cdd_data, on=['Country', 'Territory', 'Date'], how='inner')

x_data = temp_and_cdd_data['Temperaturedaily']
y_data = temp_and_cdd_data['CDDhum18dailybypop']

def exp_growth(x, a, b, c):
    """Exponential‑growth form: y = a * exp(b * x) + c"""
    return a * np.exp(b * x) + c

# 1. Clean & align vectors (just in case)
mask = (~x_data.isna()) & (~y_data.isna())
x = x_data[mask].to_numpy()
y = y_data[mask].to_numpy()

# 2. Pick smarter initial guesses
#   • a ≈ y at x ≈ 0   (baseline scale)
#   • b ≈ growth rate  (~0.05–0.2 often works)
#   • c ≈ min(y) or 0  (vertical shift)
initial_guess = [y.min() + 1, 0.07, 0]

# 3. Fit, giving curve_fit room to iterate
from scipy.optimize import curve_fit
params, cov = curve_fit(
    exp_growth, x, y,
    p0=initial_guess,
    maxfev=20_000   # plenty of evaluations
)

a_fit, b_fit, c_fit = params

# Print the fitted exponential‑growth equation
equation = f"y = {a_fit:.4f} * exp({b_fit:.4f} * x) + {c_fit:.4f}"
print("Fitted equation:", equation)

# --- Calculate R^2 ---------------------------------------------------------- 👉
y_pred = exp_growth(x, *params)      # predicted values at each observed x
r2 = r2_score(y, y_pred)
print(f"R² = {r2:.4f}")

# 4. Visualise
import matplotlib.pyplot as plt
plt.scatter(x, y, s=8, label="Observed")
xx = np.linspace(x.min(), x.max(), 300)
plt.plot(xx, exp_growth(xx, *params), lw=2, label="Exponential growth fit", color="red")
plt.xlabel("Temperature (°C)")
plt.ylabel("CDD (pop‑weighted)")
plt.legend()
plt.tight_layout()
plt.show()
