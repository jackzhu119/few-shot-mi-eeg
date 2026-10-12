[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000245-blue)](https://doi.org/10.82901/nemar.nm000245)

# Motor Imagery dataset from Cho et al 2017

Motor Imagery dataset from Cho et al 2017.

## Dataset Overview

- **Code**: Cho2017
- **Paradigm**: imagery
- **DOI**: 10.5524/100295
- **Subjects**: 52
- **Sessions per subject**: 1
- **Events**: left_hand=1, right_hand=2
- **Trial interval**: [0, 3] s
- **File format**: .mat (MATLAB)

## Acquisition

- **Sampling rate**: 512.0 Hz
- **Number of channels**: 68
- **Channel types**: eeg=64, emg=4
- **Channel names**: AF3, AF4, AF7, AF8, AFz, C1, C2, C3, C4, C5, C6, CP1, CP2, CP3, CP4, CP5, CP6, CPz, Cz, EMG1, EMG2, EMG3, EMG4, F1, F2, F3, F4, F5, F6, F7, F8, FC1, FC2, FC3, FC4, FC5, FC6, FCz, FT7, FT8, Fp1, Fp2, Fpz, Fz, Iz, O1, O2, Oz, P1, P10, P2, P3, P4, P5, P6, P7, P8, P9, PO3, PO4, PO7, PO8, POz, Pz, T7, T8, TP7, TP8
- **Montage**: standard_1005
- **Hardware**: Biosemi ActiveTwo
- **Software**: BCI2000 3.0.2
- **Reference**: CMS/DRL
- **Sensor type**: active electrodes
- **Line frequency**: 60.0 Hz
- **Electrode type**: active
- **Auxiliary channels**: EMG (4 ch)

## Participants

- **Number of subjects**: 52
- **Health status**: healthy
- **Age**: mean=24.8, std=3.86
- **Gender distribution**: female=19, male=33
- **Handedness**: {'right': 50, 'both': 2}
- **BCI experience**: collected via questionnaire (0 = no, number = how many times)
- **Species**: human

## Experimental Protocol

- **Paradigm**: imagery
- **Number of classes**: 2
- **Class labels**: left_hand, right_hand
- **Trial duration**: 3.0 s
- **Study design**: motor imagery
- **Feedback type**: none
- **Stimulus type**: visual instruction
- **Stimulus modalities**: visual
- **Primary modality**: visual
- **Mode**: offline
- **Instructions**: Subjects were asked to imagine kinesthetic finger movements (touching index, middle, ring, and little finger to thumb within 3 seconds)

## HED Event Annotations

Schema: HED 8.4.0 | Browse: https://www.hedtags.org/hed-schema-browser

```
  left_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Left, Hand

  right_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Right, Hand

```
## Paradigm-Specific Parameters

- **Detected paradigm**: motor_imagery
- **Imagery tasks**: left_hand, right_hand
- **Cue duration**: 3.0 s
- **Imagery duration**: 3.0 s

## Data Structure

- **Trials**: 100 or 120 per class (200-240 total)
- **Blocks per session**: 5 or 6
- **Trials context**: per_class

## Preprocessing

- **Data state**: raw
- **Preprocessing applied**: False
- **Notes**: Bad trial indices provided separately in .mat files (bad_trial_indices); raw EEG data is unfiltered

## Signal Processing

- **Classifiers**: FLDA
- **Feature extraction**: CSP, ERD, ERS
- **Frequency bands**: alpha=[8.0, 14.0] Hz; mu=[8, 12] Hz; analyzed=[8.0, 30.0] Hz

## Cross-Validation

- **Method**: random subset selection
- **Folds**: 10
- **Evaluation type**: within_session

## Performance (Original Study)

- **Accuracy**: 67.46%
- **Accuracy Std**: 13.17
- **Discriminative Subjects**: 38
- **Total Subjects**: 50

## BCI Application

- **Applications**: motor_control
- **Online feedback**: False

## Tags

- **Pathology**: Healthy
- **Modality**: Motor
- **Type**: Research

## Documentation

- **Description**: EEG datasets for motor imagery brain-computer interface from 52 subjects with psychological and physiological questionnaire, EMG datasets, 3D EEG electrode locations, and non-task-related states
- **DOI**: 10.5524/100295
- **Associated paper DOI**: 10.1093/gigascience/gix034
- **License**: CC-BY-4.0
- **Investigators**: Hohyun Cho, Minkyu Ahn, Sangtae Ahn, Moonyoung Kwon, Sung Chan Jun
- **Senior author**: Sung Chan Jun
- **Contact**: scjun@gist.ac.kr; TEL: +82-62-715-2216; FAX: +82-62-715-2204
- **Institution**: Gwangju Institute of Science and Technology
- **Department**: School of Electrical Engineering and Computer Science
- **Address**: 123 Cheomdangwagi-ro, Buk-gu, Gwangju 61005, Korea
- **Country**: KR
- **Repository**: GigaDB
- **Data URL**: http://dx.doi.org/10.5524/100295
- **Publication year**: 2017
- **Funding**: GIST Research Institute (GRI) grant funded by the GIST in 2017; Institute for Information & Communication Technology Promotion (IITP) grant funded by the Korea government (No. 2017-0-00451)
- **Ethics approval**: Institutional Review Board of Gwangju Institute of Science and Technology
- **Keywords**: motor imagery, EEG, brain-computer interface, performance variation, subject-to-subject transfer

## Abstract

Motor imagery (MI)-based brain-computer interface (BCI) dataset from 52 subjects with EEG, EMG, psychological and physiological questionnaire, 3D EEG electrode locations, and non-task-related states. The dataset includes 100 or 120 trials per class (left/right hand) with validation showing 73.08% (38 subjects) had discriminative information. Mean accuracy of 67.46% (±13.17%) over 50 subjects (excluding 2 bad subjects). Dataset stored in GigaDB and validated using bad trial percentage, ERD/ERS analysis, and classification analysis.

## Methodology

Subjects performed motor imagery of left and right hand finger movements (kinesthetic imagery). Each trial consisted of: 2 seconds fixation cross, 3 seconds instruction (left/right hand), followed by random 4.1-4.8 second break. Five or six runs performed with feedback after each run. Additional data collected: 6 types of non-task-related data (eye blinking, eyeball movements, head movement, jaw clenching, resting state) and 20 trials of real hand movement per class. 3D electrode coordinates measured with Polhemus Fastrak digitizer. Experiments conducted August-September 2011 in four time slots (9:30-12:00, 12:30-15:00, 15:30-18:00, 19:00-21:30) with background noise 37-39 dB.

## References

Cho, H., Ahn, M., Ahn, S., Kwon, M. and Jun, S.C., 2017. EEG datasets for motor imagery brain computer interface. GigaScience. https://doi.org/10.1093/gigascience/gix034
Appelhoff, S., Sanderson, M., Brooks, T., Vliet, M., Quentin, R., Holdgraf, C., Chaumon, M., Mikulan, E., Tavabi, K., Hochenberger, R., Welke, D., Brunner, C., Rockhill, A., Larson, E., Gramfort, A. and Jas, M. (2019). MNE-BIDS: Organizing electrophysiological data into the BIDS format and facilitating their analysis. Journal of Open Source Software 4: (1896). https://doi.org/10.21105/joss.01896

Pernet, C. R., Appelhoff, S., Gorgolewski, K. J., Flandin, G., Phillips, C., Delorme, A., Oostenveld, R. (2019). EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Scientific Data, 6, 103. https://doi.org/10.1038/s41597-019-0104-8

---
Generated by MOABB 1.5.0 (Mother of All BCI Benchmarks)
https://github.com/NeuroTechX/moabb
