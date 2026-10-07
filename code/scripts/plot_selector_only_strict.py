#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

COLORS = {'dnq_dlc_full':'#235A9F','fixed_identity':'#7F8C8D','nearest_neighbor':'#B5B5B5'}
LABELS = {'dnq_dlc_full':'Dynamic interaction','fixed_identity':'Fixed identity','nearest_neighbor':'Nearest neighbor'}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    root=Path(a.root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    src=root/'aggregate'/'randomized_attribution_rows.csv'; d=pd.read_csv(src)
    metrics=[('overtake_success_rate','Benchmark completion'),('on_track_overtake_rate','On-track overtaking'),('elegant_overtake_rate','Desirable overtaking'),('target_grass_rate','Target grass exposure')]
    rows=[]
    for alg,g in d.groupby('algorithm'):
        for metric,label in metrics:
            rows.append({'algorithm':alg,'metric':label,'mean':g[metric].mean(),'n':len(g)})
    pd.DataFrame(rows).to_csv(out/'selector_only_strict_figure_source.csv',index=False)
    fig,ax=plt.subplots(figsize=(7.2,4.2)); y=range(len(metrics)); width=.24
    for j,alg in enumerate(['dnq_dlc_full','fixed_identity','nearest_neighbor']):
        vals=[d.loc[d.algorithm==alg,m].mean() for m,_ in metrics]
        ax.bar([i+(j-1)*width for i in y],vals,width,label=LABELS[alg],color=COLORS[alg],edgecolor='white',linewidth=.6)
    ax.set_xticks(list(y),[x[1] for x in metrics]); ax.set_ylim(0,1.05); ax.set_ylabel('Episode-level rate / exposure'); ax.grid(axis='y',alpha=.25); ax.legend(frameon=False,ncol=3,loc='upper center',bbox_to_anchor=(.5,1.16)); fig.tight_layout()
    for ext in ['pdf','svg','png','tiff']: fig.savefig(out/f'figure_selector_only_strict.{ext}',dpi=400 if ext in ['png','tiff'] else None)
    plt.close(fig)

if __name__=='__main__': main()
