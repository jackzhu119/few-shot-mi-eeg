[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000140-blue)](https://doi.org/10.82901/nemar.nm000140)

# BNCI 2015-001 Motor Imagery dataset

BNCI 2015-001 Motor Imagery dataset.

## Dataset Overview

- **Code**: BNCI2015-001
- **Paradigm**: imagery
- **DOI**: 10.1109/tnsre.2012.2189584
- **Subjects**: 12
- **Sessions per subject**: 2
- **Events**: right_hand=1, feet=2
- **Trial interval**: [0, 5] s
- **File format**: gdf
- **Data preprocessed**: True

## Acquisition

- **Sampling rate**: 512.0 Hz
- **Number of channels**: 13
- **Channel types**: eeg=13
- **Channel names**: FC3, FCz, FC4, C5, C3, C1, Cz, C2, C4, C6, CP3, CPz, CP4
- **Montage**: 10-20
- **Hardware**: g.tec
- **Software**: Matlab
- **Reference**: Car
- **Sensor type**: active electrode
- **Line frequency**: 50.0 Hz
- **Online filters**: 50 Hz notch
- **Cap manufacturer**: g.tec
- **Cap model**: g.GAMMAsys
- **Auxiliary channels**: gsr

## Participants

- **Number of subjects**: 12
- **Health status**: healthy
- **Age**: mean=24.8
- **Gender distribution**: male=7, female=5
- **Handedness**: all right-handed
- **BCI experience**: naive
- **Species**: human

## Experimental Protocol

- **Paradigm**: imagery
- **Number of classes**: 2
- **Class labels**: right_hand, feet
- **Trial duration**: 11.0 s
- **Study design**: Two-class motor imagery: sustained right hand movement imagery (palmar grip) versus both feet movement imagery (plantar extension)
- **Feedback type**: visual
- **Stimulus type**: cursor_feedback
- **Stimulus modalities**: visual, auditory
- **Primary modality**: visual
- **Synchronicity**: synchronous
- **Mode**: training
- **Instructions**: Relax during reference period (3s), perform sustained kinesthetic movement imagery during activity period. Condition 1 (arrow right): imagine palmar grip with right hand. Condition 2 (arrow down): imagine plantar extension of both feet.

## HED Event Annotations

Schema: HED 8.4.0 | Browse: https://www.hedtags.org/hed-schema-browser

```
  right_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Right, Hand

  feet
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine, Move, Foot

```
## Paradigm-Specific Parameters

- **Detected paradigm**: motor_imagery
- **Imagery tasks**: right_hand_palmar_grip, both_feet_plantar_extension
- **Cue duration**: 1.25 s
- **Imagery duration**: 4.0 s

## Data Structure

- **Trials**: 200
- **Trials per class**: right_hand=100, feet=100
- **Trials context**: per_session

## Preprocessing

- **Data state**: filtered
- **Preprocessing applied**: True
- **Steps**: bandpass filter, notch filter
- **Highpass filter**: 0.5 Hz
- **Lowpass filter**: 100.0 Hz
- **Bandpass filter**: {'low_cutoff_hz': 0.5, 'high_cutoff_hz': 100.0}
- **Notch filter**: [50.0] Hz
- **Re-reference**: car

## Signal Processing

- **Classifiers**: LDA
- **Feature extraction**: logarithmic bandpower, CSP
- **Frequency bands**: alpha=[10, 13] Hz; beta=[16, 24] Hz

## Cross-Validation

- **Method**: leave-one-out
- **Evaluation type**: cross_session

## Performance (Original Study)

- **Accuracy**: 80.0%

## BCI Application

- **Applications**: communication, control
- **Online feedback**: True

## Tags

- **Pathology**: Healthy
- **Modality**: Motor
- **Type**: Motor

## Documentation

- **DOI**: 10.1109/tnsre.2012.2189584
- **License**: CC-BY-NC-ND-4.0
- **Investigators**: Josef Faller, Carmen Vidaurre, Teodoro Solis-Escalante, Christa Neuper, Reinhold Scherer
- **Senior author**: Reinhold Scherer
- **Contact**: josef.faller@tugraz.at; christa.neuper@uni-graz.at; carmen.vidaurre@tu-berlin.de
- **Institution**: Graz University of Technology
- **Department**: Institute of Knowledge Discovery
- **Address**: 8010 Graz, Austria
- **Country**: Austria
- **Repository**: BNCI Horizon
- **Publication year**: 2012
- **Funding**: FP7 Framework EU Research Project BrainAble (No. 247447)

## References

Faller, J., Vidaurre, C., Solis-Escalante, T., Neuper, C., & Scherer, R. (2012). Autocalibration and recurrent adaptation: Towards a plug and play online ERD-BCI. IEEE Transactions on Neural Systems and Rehabilitation Engineering, 20(3), 313-319. https://doi.org/10.1109/tnsre.2012.2189584

Notes

.. note::

``BNCI2015_001`` was previously named ``BNCI2015001``. ``BNCI2015001`` will be removed in version 1.1.

.. versionadded:: 0.4.0
Appelhoff, S., Sanderson, M., Brooks, T., Vliet, M., Quentin, R., Holdgraf, C., Chaumon, M., Mikulan, E., Tavabi, K., Hochenberger, R., Welke, D., Brunner, C., Rockhill, A., Larson, E., Gramfort, A. and Jas, M. (2019). MNE-BIDS: Organizing electrophysiological data into the BIDS format and facilitating their analysis. Journal of Open Source Software 4: (1896). https://doi.org/10.21105/joss.01896

Pernet, C. R., Appelhoff, S., Gorgolewski, K. J., Flandin, G., Phillips, C., Delorme, A., Oostenveld, R. (2019). EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Scientific Data, 6, 103. https://doi.org/10.1038/s41597-019-0104-8

---
Generated by MOABB 1.4.3 (Mother of All BCI Benchmarks)
https://github.com/NeuroTechX/moabb
