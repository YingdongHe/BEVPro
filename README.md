# BEVPro

BEVPro is an open source OpenAI Gym environment that simulates a regional energy network integrating buildings with distributed renewable power supply and energy storage, electric vehicles, smart microgrid, and local power grid. Its objective is to advance the smart control of regional energy networks supporting multiple buildings and electric vehicles, for enhancing energy flexibility and CO2 emission reduction simultaneously.

# Overview
With the fast increase in distributed renewable generation and electric vehicles, smart energy management strategies are needed for transformation towards a carbon-neutrality community with high energy flexibility. BEVPro allows the easy implementation of advanced control agents in a multi-agent setting to achieve customized goals: energy saving, load shifting, CO2 emission reduction, operational cost saving, and etc. 

The aimed energy network in this version:
<img src="docs/figs/Platform BEVPro.png" width="900" />

# Code Usage
### Clone repository
```
git clone https://github.com/YingdongHe/BEVPro.git
cd BEVPro
```

### Set up the environment 
Set up the virtual environment with your preferred environment/package manager.

The instruction here is based on **conda**. ([Install conda](https://docs.anaconda.com/anaconda/install/))
```
conda create --name BEVPro python=3.8 -c conda-forge -f requirements.txt
conda activate BEVPro
```

### Repository structure
```
|
├── LICENSE
│
├── README.md
│
├── requirements.txt
│
├── gym_BEVPro
│   └── envs
│   │   ├──data
│   │   ├──inputs
│   │   ├──BEVCommunity.py
│   │   ├──model.py
│   │   ├──data_cleaning.ipynb
│   │   └──Simulation.ipynb 
│   └── _init_.py
│
└── docs

```

``gym_BEVPro``: Code and data to develop the OpenAI Gym environment

``gym_BEVPro/envs/BEVCommunity.py``: Code of the environment

``gym_BEVPro/envs/model.py``: Individual models, including the model for vehicles, buildings, renewable sources, distributed energy storage etc.

``gym_BEVPro/envs/inputs``: Input file of the environment

``gym_BEVPro/envs/Simulation.ipynb``: File to establish a regional energy network with multiple buildings and vehicles and deploy smart control in the gym environment

``docs``: documents (papers, figures) related to this environment


### Running
You can set up your regional energy network and run it using the Jupyter notebook ``gym_BEVPro/envs/Simulation.ipynb``

The corresponding guidance on establishing a regional energy network and customizing energy management strategies is also represented in the above-stated file.

*Notes*
- Official Documentation of [OpenAI Gym](https://gym.openai.com/).

### Feedback

Feel free to send any questions/feedback to: [Yingdong He](mailto:heyingdong2017@berkeley.edu)

### Clarification
BEVPro is built with the basic frame of [AlphaHydrogen](https://github.com/YingdongHe/AlphaHydrogen), another work of the author.

# License
When using this software, please cite it:

Yingdong He. BEVPro. https://github.com/YingdongHe/BEVPro (2021).

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
