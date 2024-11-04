import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# set basic parameters
mpl.rcParams['pdf.fonttype'] = 42

is_black_background = False
if is_black_background:
    plt.style.use('dark_background')
    mpl.rcParams.update({"ytick.color" : "w",
                     "xtick.color" : "w",
                     "axes.labelcolor" : "w",
                     "axes.edgecolor" : "w"})

LARGE_SIZE = 16
MEDIUM_SIZE = 14
SMALLER_SIZE = 12
plt.rc('font', size=MEDIUM_SIZE)
plt.rc('axes', labelsize=MEDIUM_SIZE)
plt.rc('axes', titlesize=MEDIUM_SIZE)	 # fontsize of the axes title
plt.rc('xtick', labelsize=SMALLER_SIZE)	 # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALLER_SIZE)	 # fontsize of the tick labels
plt.rc('figure', titlesize=MEDIUM_SIZE)
plt.rc('legend', fontsize=SMALLER_SIZE)
mpl.rcParams.update({
    "pdf.use14corefonts": True
})
 #, xtick.color='w', axes.labelcolor='w', axes.edge_color='w'
FIG_HEIGHT = 4
FIG_WIDTH = 4


COLORS = {
    'Cast Iron': '#deebf7',
    'Steel': '#F7DAB5',
    'EE': '#d9f0a3', 
    'Cu': '#fec44f',
    'Al': '#ccece6',
    'Concrete': '#fbb4ae',
    'Composites': '#9ecae1',
    'Other (fractions)': '#9e9ac8',
    'Others': '#9e9ac8',
    'Nd': '#addd8e',
    'Dy': '#f7fcb9',
}

    