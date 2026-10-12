[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000135-blue)](https://doi.org/10.82901/nemar.nm000135)

# BNCI 2014-004 Motor Imagery dataset

BNCI 2014-004 Motor Imagery dataset.

## Dataset Overview

- **Code**: BNCI2014-004
- **Paradigm**: imagery
- **DOI**: 10.1109/TNSRE.2007.906956
- **Subjects**: 9
- **Sessions per subject**: 5
- **Events**: left_hand=1, right_hand=2
- **Trial interval**: [3, 7.5] s
- **Session IDs**: 01T, 02T, 03T, 04E, 05E
- **File format**: GDF

## Acquisition

- **Sampling rate**: 250.0 Hz
- **Number of channels**: 3
- **Channel types**: eeg=3, eog=3
- **Channel names**: C3, C4, Cz, EOG1, EOG2, EOG3
- **Montage**: standard_1020
- **Hardware**: g.tec
- **Software**: rtsBCI (MATLAB/Simulink)
- **Reference**: left mastoid
- **Ground**: Fz
- **Sensor type**: EEG
- **Line frequency**: 50.0 Hz
- **Online filters**: 0.5-100 Hz bandpass, 50 Hz notch
- **Cap manufacturer**: Easycap
- **Electrode material**: Ag/AgCl
- **Auxiliary channels**: EOG (3 ch, horizontal, vertical, radial)

## Participants

- **Number of subjects**: 9
- **Health status**: healthy
- **Age**: mean=24.7, std=3.3
- **Handedness**: right
- **BCI experience**: naive
- **Species**: human

## Experimental Protocol

- **Paradigm**: imagery
- **Task type**: motor_imagery
- **Number of classes**: 2
- **Class labels**: left_hand, right_hand
- **Trial duration**: 7.5 s
- **Tasks**: left_hand_imagery, right_hand_imagery
- **Study design**: Two-class motor imagery: left hand and right hand. Screening sessions (01T, 02T) without feedback, feedback sessions (03T, 04E, 05E) with smiley feedback.
- **Study domain**: brain-computer interface
- **Feedback type**: visual
- **Stimulus type**: arrow_cue
- **Stimulus modalities**: visual, auditory
- **Primary modality**: visual
- **Synchronicity**: cue_based
- **Mode**: both
- **Training/test split**: True
- **Instructions**: Subjects selected their best motor imagery strategy (e.g., squeezing a ball or pulling a brake) and performed kinesthetic motor imagery of left or right hand movements.

## HED Event Annotations

Schema: HED 8.4.0 | Browse: https://www.hedtags.org/hed-schema-browser

```
  left_hand
    ├─ Sensory-event
    │  ├─ Experimental-stimulus
    │  ├─ Visual-presentation
    │  └─ Leftward, Arrow
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Left, Hand

  right_hand
    ├─ Sensory-event
    │  ├─ Experimental-stimulus
    │  ├─ Visual-presentation
    │  └─ Rightward, Arrow
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Right, Hand

```
## Paradigm-Specific Parameters

- **Detected paradigm**: motor_imagery
- **Imagery tasks**: left_hand, right_hand
- **Cue duration**: 1.25 s
- **Imagery duration**: 4.0 s

## Data Structure

- **Trials**: {'screening': 120, 'feedback': 160}
- **Trials context**: per session

## Preprocessing

- **Data state**: raw with online filtering
- **Preprocessing applied**: True
- **Steps**: bandpass filtering, notch filtering
- **Highpass filter**: 0.5 Hz
- **Lowpass filter**: 100.0 Hz
- **Bandpass filter**: {'low_cutoff_hz': 0.5, 'high_cutoff_hz': 100.0}
- **Notch filter**: [50.0] Hz
- **Filter type**: analog
- **Notes**: Online bandpass (0.5-100 Hz) and notch (50 Hz) filters applied during recording. Artifact trials marked with event type 1023. EOG channels provided for user-applied artifact correction.

## Signal Processing

- **Classifiers**: LDA
- **Feature extraction**: Bandpower, BP

## Cross-Validation

- **Method**: 10x10 cross-validation
- **Folds**: 10
- **Evaluation type**: within_subject

## BCI Application

- **Applications**: motor_control
- **Environment**: laboratory
- **Online feedback**: True

## Tags

- **Pathology**: Healthy
- **Modality**: Motor
- **Type**: Motor Imagery

## Documentation

- **Description**: BCI Competition 2008 - Graz data set B: Two-class motor imagery dataset (left/right hand) with screening sessions (no feedback) and smiley feedback sessions. 9 subjects, 3 bipolar EEG channels (C3, Cz, C4) + 3 EOG channels, 250 Hz.
- **DOI**: 10.1109/TNSRE.2007.906956
- **License**: CC-BY-ND-4.0
- **Investigators**: R. Leeb, C. Brunner, G. R. Müller-Putz, A. Schlögl, G. Pfurtscheller, F. Lee, C. Keinrath, R. Scherer, H. Bischof
- **Senior author**: G. Pfurtscheller
- **Institution**: Graz University of Technology
- **Department**: Institute for Knowledge Discovery
- **Country**: AT
- **Repository**: BNCI Horizon
- **Data URL**: http://biosig.sourceforge.net/
- **Publication year**: 2007
- **Keywords**: brain-computer interface, BCI, electroencephalogram, EEG, motor imagery, BCI competition, smiley feedback

## External Links

- **Source**: http://biosig.sourceforge.net/

## Abstract

BCI Competition 2008 Graz data set B. EEG data from 9 subjects performing two-class motor imagery (left hand vs right hand). Two screening sessions without feedback (120 trials each) and three feedback sessions with smiley feedback (160 trials each). Three bipolar EEG channels (C3, Cz, C4) and three EOG channels recorded at 250 Hz.

## Methodology

Subjects performed kinesthetic motor imagery of left or right hand movements. Two screening sessions (01T, 02T) without feedback: 6 runs x 20 trials = 120 trials per session. Three feedback sessions (03T, 04E, 05E) with smiley feedback: 4 runs x 40 trials (20 per class) = 160 trials per session. Screening trials: fixation cross + beep at t=0, arrow cue at ~t=2 for 1.25s, imagery for 4s, break. Feedback trials: smiley at t=0, beep at t=2, cue from t=3 to t=7.5 with continuous smiley feedback. Three bipolar EEG channels (C3, Cz, C4) plus three monopolar EOG channels recorded at 250 Hz with 0.5-100 Hz bandpass and 50 Hz notch filter. EEG ground at Fz, EOG reference at left mastoid. Amplifier: g.tec. Software: rtsBCI (MATLAB/Simulink).

## References

Tangermann, M., Muller, K.R., Aertsen, A., Birbaumer, N., Braun, C., Brunner, C., Leeb, R., Mehring, C., Miller, K.J., Mueller-Putz, G. and Nolte, G., 2012. Review of the BCI competition IV. Frontiers in neuroscience, 6, p.55.

Notes

.. note::

``BNCI2014_004`` was previously named ``BNCI2014004``. ``BNCI2014004`` will be removed in version 1.1.

.. versionadded:: 0.4.0

This dataset is commonly referred to as "BCI Competition IV Dataset 2b". It is widely used for binary motor imagery classification tasks.

See Also

BNCI2014_001 : 4-class motor imagery (Dataset 2a) BNCI2014_002 : 2-class motor imagery with Laplacian derivations
Appelhoff, S., Sanderson, M., Brooks, T., Vliet, M., Quentin, R., Holdgraf, C., Chaumon, M., Mikulan, E., Tavabi, K., Hochenberger, R., Welke, D., Brunner, C., Rockhill, A., Larson, E., Gramfort, A. and Jas, M. (2019). MNE-BIDS: Organizing electrophysiological data into the BIDS format and facilitating their analysis. Journal of Open Source Software 4: (1896). https://doi.org/10.21105/joss.01896

Pernet, C. R., Appelhoff, S., Gorgolewski, K. J., Flandin, G., Phillips, C., Delorme, A., Oostenveld, R. (2019). EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Scientific Data, 6, 103. https://doi.org/10.1038/s41597-019-0104-8

---
Generated by MOABB 1.4.3 (Mother of All BCI Benchmarks)
https://github.com/NeuroTechX/moabb
