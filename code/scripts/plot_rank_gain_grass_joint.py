#!/usr/bin/env python3
"""Frozen-data diagnostic; run from multi_car_racing. No controller edits."""
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/tits-rank-matplotlib')
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/tits_dynamic_graph_expanded/current_paper_data_20260916/standard_summary_metrics.csv'
OUT = ROOT / 'outputs/tits_dynamic_graph_expanded/rank_gain_grass_joint_20260918'
OUT.mkdir(parents=True, exist_ok=True)
ORDER = ['v6_runtime_dynamic_neighborhood_safe', 'rule_expert_gate', 'rule_safety_gate',
         'dlc_individual_transition', 'dlc_joint_transition', 'dlc_joint_transition_observer',
         'ppo_continuous', 'sac_continuous', 'td3_continuous']
LABELS = dict(zip(ORDER, ['DRQ-DLC', 'Rule Expert', 'Safety Rule', 'DLC-IT', 'DLC-JT', 'DLC-JTO', 'PPO', 'SAC', 'TD3']))
COLORS = dict(zip(ORDER, ['#C45D34','#37749F','#5B8C79','#888888','#B18C64','#9A739E','#4CABB4','#BD9C43','#7984B1']))
MARKERS = dict(zip(ORDER,['o','s','^','o','s','^','o','s','^']))
KEYS = ['track_id','num_agents','seed']
RNG = np.random.default_rng(20260918)
B = 10000

def ci_seed(g, column):
    # Resample seeds, retaining all track/vehicle-count cases within each seed.
    v = g.groupby('seed')[column].agg(['sum','count']).to_numpy()
    if np.ptp(g[column].to_numpy()) == 0:
        return (float(g[column].iloc[0]),)*2
    idx=RNG.integers(0,len(v),(B,len(v)))
    means=v[idx,0].sum(axis=1)/v[idx,1].sum(axis=1)
    return tuple(np.quantile(means,[.025,.975]))

def density(values, grid, lo, hi, bandwidth):
    # Fixed, method-independent bandwidth; reflection at both physical bounds.
    v = np.asarray(values)
    out = (norm.pdf((grid[:,None]-v)/bandwidth)
           +norm.pdf((grid[:,None]-(2*lo-v))/bandwidth)
           +norm.pdf((grid[:,None]-(2*hi-v))/bandwidth)).mean(axis=1)/bandwidth
    return out

def export(fig, name):
    for ext in ['pdf','svg','png','tiff']:
        fig.savefig(OUT/f'{name}.{ext}',dpi=600 if ext=='tiff' else 240,facecolor='white')
    plt.close(fig)

def main():
    d=pd.read_csv(SOURCE)
    d=d[d.experiment_id.str.startswith(('E1','E2','E3')) & d.algorithm.isin(ORDER)].copy()
    d['dataset']=d.experiment_id.str[:2]
    assert not d.duplicated(['dataset','algorithm']+KEYS).any()
    assert np.isfinite(d[['rank_gain','target_grass_rate','num_agents']]).all().all()
    assert (d.rank_gain==d.num_agents-d.target_final_rank).all()
    assert d.target_grass_rate.between(0,1).all()
    d['normalized_rank_gain']=d.rank_gain/(d.num_agents-1)
    assert d.normalized_rank_gain.between(0,1).all()
    d['method']=d.algorithm.map(LABELS)
    d.to_csv(OUT/'source_run_level.csv',index=False)
    rows=[]
    for (ds,alg),g in d.groupby(['dataset','algorithm']):
        for metric in ['rank_gain','normalized_rank_gain','target_grass_rate','target_mean_speed']:
            low,high=ci_seed(g,metric)
            rows.append(dict(dataset=ds,algorithm=alg,method=LABELS[alg],metric=metric,n=len(g),
                             seeds=g.seed.nunique(),mean=g[metric].mean(),ci_low=low,ci_high=high,
                             interval='95% seed-cluster percentile bootstrap; 10000 resamples'))
    summary=pd.DataFrame(rows)
    summary.to_csv(OUT/'summary_by_dataset.csv',index=False)
    paired=[]
    for ds,g in d.groupby('dataset'):
        ours=g[g.algorithm==ORDER[0]]
        for alg in ORDER[1:]:
            other=g[g.algorithm==alg]
            if other.empty: continue
            m=ours.merge(other,on=KEYS,suffixes=('_ours','_other'),validate='one_to_one')
            assert len(m)==len(ours)==len(other)
            for metric in ['rank_gain','normalized_rank_gain','target_grass_rate']:
                v=m[metric+'_ours']-m[metric+'_other']
                temp=pd.DataFrame({'seed':m.seed,'delta':v})
                low,high=ci_seed(temp,'delta')
                paired.append(dict(dataset=ds,comparator=LABELS[alg],metric=metric,n=len(m),
                                   mean_delta_ours_minus_other=v.mean(),ci_low=low,ci_high=high))
    pd.DataFrame(paired).to_csv(OUT/'paired_deltas.csv',index=False)
    e=d[d.dataset=='E1']
    ref=set(map(tuple,e[e.algorithm==ORDER[0]][KEYS].to_numpy()))
    for alg in ORDER:
        assert set(map(tuple,e[e.algorithm==alg][KEYS].to_numpy()))==ref
    assert len(ref)==164
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'axes.labelsize':7,
                         'axes.titlesize':8,'axes.linewidth':.6,'pdf.fonttype':42,'svg.fonttype':'none',
                         'legend.fontsize':6.4,'xtick.labelsize':6.4,'ytick.labelsize':6.4})
    # A matched E1 view, separated into method families to avoid nine overlapping distributions.
    fig=plt.figure(figsize=(183/25.4,112/25.4))
    outer=fig.add_gridspec(1,3,left=.075,right=.985,bottom=.27,top=.88,wspace=.27)
    groups=[ORDER[:3],ORDER[3:6],ORDER[6:]]
    titles=['a  Proposed and rule controllers','b  DLC references','c  Model-free references']
    for k,(group,title) in enumerate(zip(groups,titles)):
        gs=outer[k].subgridspec(2,2,height_ratios=[1,3.4],width_ratios=[3.4,1],hspace=.08,wspace=.08)
        ax=fig.add_subplot(gs[1,0]); top=fig.add_subplot(gs[0,0],sharex=ax); right=fig.add_subplot(gs[1,1],sharey=ax)
        note=fig.add_subplot(gs[0,1]); note.axis('off')
        if k==1: note.text(.02,.5,'Rank gain:\nall zero',fontsize=6,va='center')
        # Identical limits and fixed bandwidths across all method families.
        gridx=np.linspace(0,7,501); gridy=np.linspace(0,1,501)
        for j,alg in enumerate(group):
            q=e[e.algorithm==alg]; c=COLORS[alg]; marker=MARKERS[alg]
            ax.scatter(q.rank_gain,q.target_grass_rate,s=11,alpha=.3,color=c,marker=marker,linewidths=.2,edgecolors=c)
            mx=q.rank_gain.mean(); my=q.target_grass_rate.mean()
            ax.scatter([mx],[my],s=44,marker='D',facecolors=c,edgecolors='black',linewidths=.7,zorder=6)
            # KDE is a descriptive smoothing of discrete rank gain; point masses are not smoothed.
            if q.rank_gain.nunique()>1:
                den=density(q.rank_gain,gridx,0,7,.4)
                top.plot(gridx,den,color=c,lw=1,ls=['-','--',':'][j])
                top.fill_between(gridx,0,den,color=c,alpha=.07)
            else:
                # Offset marker HEIGHT only to expose coincident masses at exactly x=0.
                top.plot([0],[.3+.32*j],marker=marker,color=c,ms=4,clip_on=False)
            if q.target_grass_rate.nunique()>1:
                den=density(q.target_grass_rate,gridy,0,1,.05)
                right.plot(den,gridy,color=c,lw=1,ls=['-','--',':'][j])
                right.fill_betweenx(gridy,0,den,color=c,alpha=.07)
            else:
                right.plot([.4+j*.4],[q.target_grass_rate.iloc[0]],marker=marker,color=c,ms=4,clip_on=False)
        ax.set_xlim(-.18,7.25); ax.set_ylim(-.025,1.025)
        ax.set_xticks([0,2,4,6]); ax.set_yticks([0,.25,.5,.75,1])
        ax.set_xlabel('Rank gain (positions)')
        if k==0: ax.set_ylabel('Grass exposure fraction')
        ax.grid(color='#E8E8E8',lw=.4)
        top.set_ylim(0,2.1); right.set_xlim(0,18)
        top.tick_params(axis='x',labelbottom=False,bottom=False); top.set_yticks([])
        right.tick_params(axis='y',labelleft=False,left=False); right.set_xticks([])
        top.set_ylabel('Density',fontsize=6); right.set_xlabel('Density',fontsize=6)
        for a in [ax,top,right]: a.spines[['top','right']].set_visible(False)
        top.set_title(title,loc='left',pad=8,fontsize=7.5)
        handles=[Line2D([],[],color=COLORS[a],marker=MARKERS[a],lw=1,ms=4,label=LABELS[a]) for a in group]
        ax.legend(handles=handles,loc='upper left',bbox_to_anchor=(-.02,-.25),frameon=False,ncol=1,handlelength=1.5,labelspacing=.35)
    fig.suptitle('E1 matched cases: ranking gain versus grass exposure',fontsize=10,y=.98)
    fig.text(.075,.045,'164 cases per method; each point is one run; diamonds show method means.',fontsize=7)
    fig.text(.075,.012,'Rank uses visited-tile counts (diagnostic proxy). Marginal curves are descriptive KDEs; zero-variance data use point masses.',fontsize=6)
    export(fig,'figure_joint_E1')
    # Means are plotted separately: one mean per method cannot define a run-level density.
    fig,axs=plt.subplots(1,3,figsize=(183/25.4,99/25.4),sharey=True)
    fig.subplots_adjust(left=.18,right=.985,bottom=.21,top=.86,wspace=.13)
    for k,ds in enumerate(['E1','E2','E3']):
        ax=axs[k]
        for j,alg in enumerate(ORDER):
            s=summary[(summary.dataset==ds)&(summary.algorithm==alg)&(summary.metric=='rank_gain')]
            if s.empty:
                ax.text(.2,j,'Not evaluated',va='center',fontsize=6,color='#888888');continue
            r=s.iloc[0]
            if ds == 'E2':
                ax.plot(r['mean'],j,color=COLORS[alg],marker=MARKERS[alg],ms=4)
            else:
                ax.errorbar(r['mean'],j,xerr=[[r['mean']-r.ci_low],[r.ci_high-r['mean']]],color=COLORS[alg],marker=MARKERS[alg],ms=4,lw=1,capsize=2)
        ax.set_yticks(range(len(ORDER)),[LABELS[a] for a in ORDER]);ax.set_ylim(8.6,-.6);ax.set_xlim(-.15,6)
        ax.set_xticks([0,2,4,6]);ax.axvline(0,color='#AAAAAA',lw=.6);ax.grid(axis='x',lw=.4,color='#EEEEEE')
        ax.spines[['top','right']].set_visible(False)
        ax.set_xlabel('Mean rank gain (positions)')
        n={'E1':164,'E2':75,'E3':50}[ds]; seeds={'E1':40,'E2':5,'E3':5}[ds]
        ax.set_title(f'{chr(97+k)}  {ds}: {n} cases, {seeds} seeds',loc='left')
    fig.suptitle('Average ranking improvement by evaluation protocol',fontsize=10,y=.96)
    fig.text(.18,.09,'E1/E3 bars: 95% seed-cluster bootstrap intervals. E2: descriptive means; outcomes repeat across seeds.',fontsize=6.5)
    fig.text(.18,.045,'Rank is a visited-tile proxy. E3 has five seed clusters; these intervals do not establish independent replication.',fontsize=6)
    export(fig,'figure_mean_rank_gain')
    manifest=dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  n_rows=len(d),e1_cases=164,bootstrap_resamples=B,bootstrap_seed=20260918,
                  rank_definition='num_agents - target_final_rank; final rank computed from visited-tile counts',
                  grass_definition='summary target_grass_rate after initialization grace period; not a collision metric',
                  kde='fixed Gaussian bandwidth: rank 0.4 positions, grass 0.05; reflected at support bounds; no KDE for zero variance',
                  caution='Post-hoc descriptive analysis. Do not pool methods with unequal E1-E3 coverage. No causal/safety superiority inference.')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(summary[summary.metric.isin(['rank_gain','target_grass_rate'])].to_string(index=False))
    print('Outputs:',OUT)

if __name__=='__main__': main()
