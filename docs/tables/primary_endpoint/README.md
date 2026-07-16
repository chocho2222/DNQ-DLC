# E1 matched overtaking-success primary endpoint

This package analyses the frozen 200-case-per-algorithm E1 source table. Cases are paired by benchmark, vehicle count, and simulator seed.

DNQ-DLC succeeded in 171/200 cases and Rule Expert in 143/200. The paired difference is +0.140 (95% paired bootstrap CI 0.065 to 0.215). Discordant pairs are 46 DNQ-DLC-only successes and 18 Rule-Expert-only successes; the two-sided exact McNemar p value is 0.000617.

The package contains all six comparator effects, the four-cell pairing audit, vehicle-count strata, a machine-readable JSON report, and the generating Python script. It supports a complete-framework advantage in the evaluated simulator benchmark, not a causal success effect from dynamic neighbor selection alone.
