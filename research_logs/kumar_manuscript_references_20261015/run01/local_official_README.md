[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000177-blue)](https://doi.org/10.82901/nemar.nm000177)

# Multi-session longitudinal motor imagery EEG dataset (Kumar et al. 2024)

## Overview

A longitudinal motor imagery EEG dataset from 18 BCI-naive subjects across 6 sessions (1 offline + 5 online) demonstrating transfer learning for brain-computer interface skill acquisition. The study compares two domain adaptation frameworks—Generic Recentering (unsupervised) and Personally Assisted Recentering (supervised)—for calibration-free BCI training using left/right hand motor imagery with visual feedback. Data were acquired at 512 Hz using 22 EEG channels and processed with Riemannian geometry-based classifiers.

## Dataset Summary

| Property | Value |
|---|---|
| Subjects | 18 |
| Channels | 22 |
| Classes | 2 |
| Trial length | 5 s |
| Sampling frequency | 512 Hz |
| Sessions | 6 |
| Total trials | 7156 |
| Paradigm | MotorImagery |

## Data Collection Methods

EEG data were recorded from 18 healthy subjects (age mean=23.22±3.59 years) across 6 sessions using ANT Neuro eego mylab hardware with 22 EEG channels and 3 EOG channels at 512 Hz sampling rate. Subjects performed cue-based left/right hand motor imagery tasks with continuous visual feedback across bar-feedback runs and car racing games. Session 1 consisted of 4 offline runs (80 trials); sessions 2-6 included 3-4 online runs each. EEG signals were bandpass filtered at 8-30 Hz using second-order Butterworth filters. Features were extracted as covariance matrices and classified using Riemannian Minimum Distance to Mean decoder.

## How to Access via MOABB

Install MOABB and load this dataset directly:

```python
from moabb.datasets import Kumar2024
from moabb.paradigms import MotorImagery
paradigm = MotorImagery()

dataset = Kumar2024()
X, y, metadata = paradigm.get_data(dataset)
```

For more details see the [MOABB documentation](https://moabb.neurotechx.com/) and the
[MOABB dataset page](https://moabb.neurotechx.com/docs/generated/moabb.datasets.Kumar2024.html).

## Citation

If you use this dataset please cite the primary publication:

> DOI: [10.1093/pnasnexus/pgae076](https://doi.org/10.1093/pnasnexus/pgae076)

## NEMAR / MOABB Benchmark Collection

This BIDS-formatted dataset was converted from the original data using the
[MOABB](https://moabb.neurotechx.com/) pipeline and re-hosted on
[NEMAR](https://nemar.org/) as part of the MOABB benchmark collection.
The original data and license terms apply — see `dataset_description.json` for details.
