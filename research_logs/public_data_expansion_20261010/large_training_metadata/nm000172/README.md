[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000172-blue)](https://doi.org/10.82901/nemar.nm000172)

# High-gamma dataset described in Schirrmeister et al. 2017

High-gamma dataset described in Schirrmeister et al. 2017.

## Dataset Overview

- **Code**: Schirrmeister2017
- **Paradigm**: imagery
- **DOI**: 10.1002/hbm.23730
- **Subjects**: 14
- **Sessions per subject**: 1
- **Events**: right_hand=1, left_hand=2, rest=3, feet=4
- **Trial interval**: [0, 4] s
- **Runs per session**: 2
- **File format**: EDF

## Acquisition

- **Sampling rate**: 500.0 Hz
- **Number of channels**: 128
- **Channel types**: eeg=128
- **Channel names**: Fp1, Fp2, Fpz, F7, F3, Fz, F4, F8, FC5, FC1, FC2, FC6, M1, T7, C3, Cz, C4, T8, M2, CP5, CP1, CP2, CP6, P7, P3, Pz, P4, P8, POz, O1, Oz, O2, AF7, AF3, AF4, AF8, F5, F1, F2, F6, FC3, FCz, FC4, C5, C1, C2, C6, CP3, CPz, CP4, P5, P1, P2, P6, PO5, PO3, PO4, PO6, FT7, FT8, TP7, TP8, PO7, PO8, FT9, FT10, TPP9h, TPP10h, PO9, PO10, P9, P10, AFF1, AFz, AFF2, FFC5h, FFC3h, FFC4h, FFC6h, FCC5h, FCC3h, FCC4h, FCC6h, CCP5h, CCP3h, CCP4h, CCP6h, CPP5h, CPP3h, CPP4h, CPP6h, PPO1, PPO2, I1, Iz, I2, AFp3h, AFp4h, AFF5h, AFF6h, FFT7h, FFC1h, FFC2h, FFT8h, FTT9h, FTT7h, FCC1h, FCC2h, FTT8h, FTT10h, TTP7h, CCP1h, CCP2h, TTP8h, TPP7h, CPP1h, CPP2h, TPP8h, PPO9h, PPO5h, PPO6h, PPO10h, POO9h, POO3h, POO4h, POO10h, OI1h, OI2h
- **Montage**: standard_1005
- **Software**: BCI2000
- **Sensor type**: EEG
- **Line frequency**: 50.0 Hz

## Participants

- **Number of subjects**: 14
- **Health status**: healthy
- **Age**: mean=27.2, std=3.6
- **Gender distribution**: female=6, male=8
- **Handedness**: {'right': 12, 'left': 2}

## Experimental Protocol

- **Paradigm**: imagery
- **Number of classes**: 4
- **Class labels**: right_hand, left_hand, rest, feet
- **Trial duration**: 4.0 s
- **Study design**: Executed movements including left hand (sequential finger-tapping), right hand (sequential finger-tapping), feet (repetitive toe clenching), and rest conditions
- **Stimulus type**: visual
- **Stimulus modalities**: visual
- **Primary modality**: visual
- **Synchronicity**: cue-based
- **Mode**: offline
- **Training/test split**: True
- **Instructions**: Subjects performed repetitive movements at their own pace when arrow was showing
- **Stimulus presentation**: type=gray arrow on black background, direction_mapping=downward=feet, leftward=left_hand, rightward=right_hand, upward=rest

## HED Event Annotations

Schema: HED 8.4.0 | Browse: https://www.hedtags.org/hed-schema-browser

```
  right_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Right, Hand

  left_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Left, Hand

  rest
    ├─ Sensory-event
    ├─ Experimental-stimulus
    ├─ Visual-presentation
    └─ Rest

  feet
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine, Move, Foot

```
## Paradigm-Specific Parameters

- **Detected paradigm**: motor_imagery
- **Imagery tasks**: left_hand_finger_tapping, right_hand_finger_tapping, feet_toe_clenching, rest

## Data Structure

- **Trials**: {'total_per_subject': 963, 'training_set': 880, 'test_set': 160}
- **Trials per class**: per_class_per_subject=260
- **Blocks per session**: 13
- **Trials context**: 13 runs per subject, 80 trials per run (4 seconds each), 3-4 seconds inter-trial interval, pseudo-randomized presentation with all 4 classes shown every 4 trials

## Signal Processing

- **Classifiers**: Deep ConvNet, Shallow ConvNet, ResNet, FBCSP with LDA
- **Feature extraction**: FBCSP, CSP, Bandpower, Spectral power modulations
- **Frequency bands**: alpha=[7.0, 13.0] Hz; beta=[13.0, 30.0] Hz; gamma=[30.0, 100.0] Hz
- **Spatial filters**: CSP

## Cross-Validation

- **Method**: holdout
- **Evaluation type**: within_subject

## Performance (Original Study)

- **Fbcsp Accuracy**: 91.2
- **Deep Convnet Accuracy**: 89.3
- **Shallow Convnet Accuracy**: 92.5

## BCI Application

- **Applications**: motor_control
- **Environment**: laboratory
- **Online feedback**: False

## Tags

- **Pathology**: Healthy
- **Modality**: Motor
- **Type**: Motor Imagery, Motor Execution

## Documentation

- **DOI**: 10.1002/hbm.23730
- **License**: CC-BY-4.0
- **Investigators**: Robin Tibor Schirrmeister, Jost Tobias Springenberg, Lukas Dominique Josef Fiederer, Martin Glasstetter, Katharina Eggensperger, Michael Tangermann, Frank Hutter, Wolfram Burgard, Tonio Ball
- **Senior author**: Tonio Ball
- **Contact**: robin.schirrmeister@uniklinik-freiburg.de
- **Institution**: University of Freiburg
- **Department**: Translational Neurotechnology Lab, Epilepsy Center, Medical Center
- **Address**: Engelberger Str. 21, Freiburg 79106, Germany
- **Country**: DE
- **Repository**: GitHub
- **Data URL**: https://web.gin.g-node.org/robintibor/high-gamma-dataset/
- **Publication year**: 2017
- **Funding**: BrainLinks-BrainTools Cluster of Excellence (DFG) EXC1086; Federal Ministry of Education and Research (BMBF) Motor-BIC 13GW0053D
- **Ethics approval**: Approved by the ethical committee of the University of Freiburg
- **Acknowledgements**: Funded by BrainLinks-BrainTools Cluster of Excellence (DFG, EXC1086) and the Federal Ministry of Education and Research (BMBF, Motor-BIC 13GW0053D).
- **How to acknowledge**: Please cite: Schirrmeister et al. (2017). Deep learning with convolutional neural networks for EEG decoding and visualization. Human Brain Mapping, 38(11), 5391-5420. https://doi.org/10.1002/hbm.23730
- **Keywords**: electroencephalography, EEG analysis, machine learning, end-to-end learning, brain-machine interface, brain-computer interface, model interpretability, brain mapping

## Abstract

Deep learning with convolutional neural networks (deep ConvNets) has revolutionized computer vision through end-to-end learning. This study investigates deep ConvNets for end-to-end EEG decoding of imagined or executed movements from raw EEG. Results show that recent advances including batch normalization and exponential linear units, together with a cropped training strategy, boosted decoding performance to match or exceed FBCSP (82.1% FBCSP vs 84.0% deep ConvNets). Novel visualization methods demonstrated that ConvNets learned to use spectral power modulations in alpha, beta, and high gamma frequencies with meaningful spatial distributions.

## Methodology

End-to-end deep learning approach comparing shallow ConvNets, deep ConvNets, and ResNets against FBCSP baseline. Evaluated design choices including batch normalization, exponential linear units, dropout, and cropped training strategies. Novel visualization techniques developed to understand learned features and verify that ConvNets use spectral power modulations in task-relevant frequency bands.

## References

Schirrmeister, Robin Tibor, et al. "Deep learning with convolutional neural networks for EEG decoding and visualization." Human brain mapping 38.11 (2017): 5391-5420.
Appelhoff, S., Sanderson, M., Brooks, T., Vliet, M., Quentin, R., Holdgraf, C., Chaumon, M., Mikulan, E., Tavabi, K., Hochenberger, R., Welke, D., Brunner, C., Rockhill, A., Larson, E., Gramfort, A. and Jas, M. (2019). MNE-BIDS: Organizing electrophysiological data into the BIDS format and facilitating their analysis. Journal of Open Source Software 4: (1896). https://doi.org/10.21105/joss.01896

Pernet, C. R., Appelhoff, S., Gorgolewski, K. J., Flandin, G., Phillips, C., Delorme, A., Oostenveld, R. (2019). EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Scientific Data, 6, 103. https://doi.org/10.1038/s41597-019-0104-8

---
Generated by MOABB 1.5.0 (Mother of All BCI Benchmarks)
https://github.com/NeuroTechX/moabb
