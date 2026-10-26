"""Publication-quality figures from saved V2 results only; no model or EEG access."""
from pathlib import Path
import argparse
import csv
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('packet', type=Path)
parser.add_argument('--analysis', type=Path, default=Path(__file__).resolve().parent)
args = parser.parse_args()
root, analysis = args.packet.resolve(), args.analysis.resolve()
out = analysis / 'figures'
out.mkdir(exist_ok=True)

def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))

summary = json.loads((root / 'analysis/summary.json').read_text())
sessions = rows(root / 'analysis/session_metrics.csv')
budgets = [4, 8, 12, 16, 20]
people = ['sub-1', 'sub-4', 'sub-7', 'sub-10', 'sub-13', 'sub-16']
colors = {'frozen':'#6d747c', 'lda_only':'#7b843e', 'full_csp':'#3474a0',
          'ea_csp':'#d08a2c', 'ea_empirical_anchored_csp':'#754889',
          'head':'#3474a0', 'full':'#d08a2c', 'l2sp':'#754889'}
labels = {'frozen':'Frozen', 'lda_only':'LDA-only', 'full_csp':'Full CSP/LDA',
          'ea_csp':'EA-CSP', 'ea_empirical_anchored_csp':'EA + empirical anchor',
          'head':'Head update', 'full':'Full update', 'l2sp':'L2-SP'}
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10,
                     'axes.spines.top':False, 'axes.spines.right':False,
                     'svg.fonttype':'none', 'pdf.fonttype':42})
figures = []

def save(fig, name):
    fig.savefig(out / (name + '.png'), dpi=600, bbox_inches='tight', facecolor='white')
    fig.savefig(out / (name + '.svg'), bbox_inches='tight', facecolor='white')
    figures.append((fig, name))

def line_axis(axis):
    axis.set_xticks(budgets)
    axis.set_xlabel('Target support-label cap')
    axis.grid(axis='y', color='#e7e7e7', linewidth=.7)
    axis.set_axisbelow(True)

fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.5), layout='constrained')
for method in ['frozen','lda_only','full_csp','ea_csp','ea_empirical_anchored_csp']:
    subset = sorted([r for r in summary['cohorts'] if r['family']=='classical' and r['method']==method], key=lambda r:r['budget'])
    axes[0].plot(budgets, [r['mean_balanced_accuracy']*100 for r in subset],
                 marker='o', color=colors[method], label=labels[method], linewidth=1.8)
line_axis(axes[0])
axes[0].set(ylabel='Target balanced accuracy (%)', ylim=(45,80), title='A  Matched-label classical comparisons')
axes[0].axhline(50, color='#b1b1b1', linewidth=.8, linestyle=':')
axes[0].legend(frameon=False, fontsize=9, loc='lower right')
contrasts = sorted([r for r in summary['comparisons'] if r['family']=='classical' and r['reference']=='ea_csp'], key=lambda r:r['budget'])
values = np.array([r['mean_difference_pp'] for r in contrasts])
low = np.array([r['ci_low_pp'] for r in contrasts])
high = np.array([r['ci_high_pp'] for r in contrasts])
axes[1].errorbar(budgets, values, yerr=[values-low,high-values], fmt='o',
                  color=colors['ea_empirical_anchored_csp'], capsize=4, linewidth=1.6)
axes[1].scatter([20], [values[-1]], marker='D', s=60, color=colors['ea_empirical_anchored_csp'], zorder=3)
axes[1].axhline(0, color='#333333', linewidth=.9)
line_axis(axes[1])
axes[1].set(ylabel='Candidate minus EA-CSP (percentage points)', title='B  Declared candidate contrast', ylim=(-6,6))
axes[1].annotate('Prespecified primary cap', xy=(20,values[-1]), xytext=(11,4.9),
                  arrowprops={'arrowstyle':'-','color':'#555555'}, fontsize=9)
fig.suptitle('Six previously exposed development participants; all fixed sessions retained', fontsize=12)
save(fig, '01_budget_and_primary_contrast')

fig = plt.figure(figsize=(11.2,9.2), layout='constrained')
grid = fig.add_gridspec(2,2, height_ratios=[.9,1])
ax = fig.add_subplot(grid[0,:])
for method in ['frozen','lda_only','full_csp','ea_csp','ea_empirical_anchored_csp']:
    values = [np.mean([float(r['balanced_accuracy']) for r in sessions if r['family']=='classical' and r['method']==method and int(r['budget'])==20 and r['session']=='ses-'+str(s)])*100 for s in range(1,6)]
    ax.plot(range(1,6),values,marker='o',color=colors[method],label=labels[method],linewidth=1.8)
ax.set(xticks=range(1,6), xlabel='Target session', ylabel='Balanced accuracy (%)', ylim=(40,85),title='A  Longitudinal means at the 20-label cap')
ax.grid(axis='y', color='#e7e7e7')
ax.legend(frameon=False, ncol=3, fontsize=9)
heat = rows(analysis / 'classical/classical_participant_session_budget20.csv')
index = {(r['participant'],r['session']):r for r in heat}
arrays = [np.array([[float(index[p,'ses-'+str(s)][key]) for s in range(1,6)] for p in people])
          for key in ['candidate_vs_ea_pp','candidate_vs_frozen_pp']]
limit = max(10, float(np.ceil(max(np.abs(a).max() for a in arrays)/5)*5))
cmap = LinearSegmentedColormap.from_list('signed_gain', ['#d28d35','#fbfaf7','#68447f'])
axes = []
for i,(array,title) in enumerate(zip(arrays,['B  Candidate minus EA-CSP','C  Candidate minus frozen'])):
    ax = fig.add_subplot(grid[1,i]);axes.append(ax)
    image = ax.imshow(array, cmap=cmap, vmin=-limit, vmax=limit, aspect='auto')
    ax.set(xticks=range(5),xticklabels=['1','2','3','4','5'],yticks=range(6),yticklabels=people,
           xlabel='Target session',title=title)
    for row in range(6):
        for col in range(5):
            ax.text(col,row,f'{array[row,col]:+.1f}',ha='center',va='center',fontsize=9,
                    color='white' if abs(array[row,col])>limit*.65 else '#222222')
fig.colorbar(image, ax=axes, shrink=.75, label='BA difference (percentage points)')
save(fig,'02_longitudinal_and_individual_gains')

fig, axes = plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
for method in ['frozen','head','full','l2sp']:
    subset=sorted([r for r in summary['cohorts'] if r['family']=='eegnet' and r['method']==method],key=lambda r:r['budget'])
    axes[0].plot(budgets,[r['mean_balanced_accuracy']*100 for r in subset],marker='o',
                  linewidth=1.7,color=colors[method],label=labels[method],linestyle='--' if method=='l2sp' else '-')
line_axis(axes[0]);axes[0].set(ylabel='Balanced accuracy (%)',ylim=(45,80),title='A  EEGNet target performance')
axes[0].axhline(50,color='#b1b1b1',linestyle=':',linewidth=.8);axes[0].legend(frameon=False,fontsize=9)
collapse=rows(analysis / 'neural/collapse_by_method_budget.csv')
methods=['frozen','head','full','l2sp']
rates=[float(next(r for r in collapse if r['method']==m and int(r['budget'])==20)['mean_participant_collapse_rate'])*100 for m in methods]
axes[1].bar(range(4),rates,color=[colors[m] for m in methods],width=.65)
axes[1].set(xticks=range(4),xticklabels=['Frozen','Head','Full','L2-SP'],ylabel='Single-class prediction rate (%)',ylim=(0,25),title='B  Collapse at the 20-label cap')
for i,value in enumerate(rates):axes[1].text(i,value+.5,f'{value:.1f}%',ha='center',fontsize=9)
axes[1].text(.02,.97,'6 participants × 3 seeds × 5 sessions\n90 nested evaluations per method',transform=axes[1].transAxes,va='top',fontsize=8)
history=rows(analysis / 'neural/source_epoch_participant_means.csv')
for key,label,color in [('mean_train_ce','Training CE','#3474a0'),('mean_validation_ce','Validation CE','#d08a2c')]:
    values=[np.mean([float(r[key]) for r in history if int(r['epoch'])==e]) for e in range(1,101)]
    axes[2].plot(range(1,101),values,label=label,color=color,linewidth=1.8)
axes[2].set(xlabel='Source epoch',ylabel='Cross-entropy',ylim=(0,1.05),title='C  Source fit and generalization')
axes[2].legend(frameon=False,fontsize=9);axes[2].grid(axis='y',color='#e7e7e7')
save(fig,'03_neural_generalization_and_collapse')

fig,axes=plt.subplots(1,2,figsize=(11.2,4.7),layout='constrained')
weights=rows(analysis/'mechanism/weight_budget_summary.csv')
for method,label,color in [('ea_anchored_csp','Fixed weight, EA','#6d747c'),
                           ('empirical_anchored_csp','Empirical weight, without EA','#d08a2c'),
                           ('ea_empirical_anchored_csp','Empirical weight, with EA','#754889')]:
    selected=sorted([r for r in weights if r['method']==method],key=lambda r:int(r['budget']))
    axes[0].plot(budgets,[float(r['participant_balanced_mean']) for r in selected],marker='o',color=color,label=label,linewidth=1.8)
line_axis(axes[0]);axes[0].set(ylabel='Mean target covariance weight (alpha)',ylim=(0,1),title='A  Saved classwise covariance weights')
axes[0].legend(frameon=False,fontsize=9,loc='upper left')
joint=rows(analysis/'mechanism/participant_weight_and_saved_gain.csv')
# Exact columns are recorded by the mechanism analysis; only descriptive dots.
selected=[r for r in joint if int(r['budget'])==20]
for r in selected:
    x=float(r['mean_class_target_weight']);y=float(r['candidate_minus_ea_pp'])
    axes[1].scatter(x,y,color='#754889',s=40)
    axes[1].annotate(r['participant'],(x,y),xytext=(4,5),textcoords='offset points',fontsize=9)
axes[1].axhline(0,color='#333333',linewidth=.9)
axes[1].set(xlabel='Participant mean target weight at cap20',ylabel='Candidate minus EA-CSP (pp)',
            xlim=(.3,.85),ylim=(-7,5),title='B  Weight magnitude and observed gain')
axes[1].text(.03,.03,'Descriptive only; no fitted selector',transform=axes[1].transAxes,fontsize=9)
save(fig,'04_anchoring_behavior')

with PdfPages(out/'V2_Analysis_Figures.pdf') as pdf:
    for figure,name in figures:
        pdf.savefig(figure,bbox_inches='tight')
        plt.close(figure)
print(json.dumps({'figure_sets':len(figures),'output':str(out),'formats':['600dpi PNG','SVG','multipage PDF']}))
