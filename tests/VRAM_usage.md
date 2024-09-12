Before loading  DeepSeek-Coder-V2-Lite     lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf

```
prokop@GTX3090:~$ nvidia-smi
Thu Sep 12 17:03:55 2024       
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.161.08             Driver Version: 535.161.08   CUDA Version: 12.2     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
|   0  NVIDIA GeForce RTX 3090        On  | 00000000:2D:00.0  On |                  N/A |
|  0%   58C    P5              53W / 420W |   1697MiB / 24576MiB |      0%      Default |
|                                         |                      |                  N/A |
+-----------------------------------------+----------------------+----------------------+
                                                                                         
+---------------------------------------------------------------------------------------+
| Processes:                                                                            |
|  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
|        ID   ID                                                             Usage      |
|=======================================================================================|
|    0   N/A  N/A      2327      G   /usr/lib/xorg/Xorg                         1213MiB |
|    0   N/A  N/A      2595      G   xfwm4                                         6MiB |
|    0   N/A  N/A      3251      G   ...erProcess --variations-seed-version      196MiB |
|    0   N/A  N/A      4690      G   ...seed-version=20240911-050142.916000      100MiB |
|    0   N/A  N/A     77203      G   ...ures=SpareRendererForSitePerProcess       98MiB |
+---------------------------------------------------------------------------------------+
```

After loading  DeepSeek-Coder-V2-Lite     lmstudio-community/DeepSeek-Coder-V2-Lite-Instruct-GGUF/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf


```
prokop@GTX3090:~$ nvidia-smi
Thu Sep 12 17:04:46 2024       
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.161.08             Driver Version: 535.161.08   CUDA Version: 12.2     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
|   0  NVIDIA GeForce RTX 3090        On  | 00000000:2D:00.0  On |                  N/A |
|  0%   61C    P2             132W / 420W |  13039MiB / 24576MiB |      0%      Default |
|                                         |                      |                  N/A |
+-----------------------------------------+----------------------+----------------------+
                                                                                         
+---------------------------------------------------------------------------------------+
| Processes:                                                                            |
|  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
|        ID   ID                                                             Usage      |
|=======================================================================================|
|    0   N/A  N/A      2327      G   /usr/lib/xorg/Xorg                         1213MiB |
|    0   N/A  N/A      2595      G   xfwm4                                         6MiB |
|    0   N/A  N/A      3251      G   ...erProcess --variations-seed-version      182MiB |
|    0   N/A  N/A      4690      G   ...seed-version=20240911-050142.916000      100MiB |
|    0   N/A  N/A     77203      G   ...ures=SpareRendererForSitePerProcess      121MiB |
|    0   N/A  N/A     78691      C   ...ures=SpareRendererForSitePerProcess    11330MiB |
+---------------------------------------------------------------------------------------+
```

After Starting Server
```
prokop@GTX3090:~$ nvidia-smi
Thu Sep 12 17:07:39 2024       
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.161.08             Driver Version: 535.161.08   CUDA Version: 12.2     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
|   0  NVIDIA GeForce RTX 3090        On  | 00000000:2D:00.0  On |                  N/A |
|  0%   59C    P8              50W / 420W |  13103MiB / 24576MiB |      5%      Default |
|                                         |                      |                  N/A |
+-----------------------------------------+----------------------+----------------------+
                                                                                         
+---------------------------------------------------------------------------------------+
| Processes:                                                                            |
|  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
|        ID   ID                                                             Usage      |
|=======================================================================================|
|    0   N/A  N/A      2327      G   /usr/lib/xorg/Xorg                         1261MiB |
|    0   N/A  N/A      2595      G   xfwm4                                         6MiB |
|    0   N/A  N/A      3251      G   ...erProcess --variations-seed-version      212MiB |
|    0   N/A  N/A      4690      G   ...seed-version=20240911-050142.916000       91MiB |
|    0   N/A  N/A     77203      G   ...ures=SpareRendererForSitePerProcess      116MiB |
|    0   N/A  N/A     78691      C   ...ures=SpareRendererForSitePerProcess    11330MiB |
+---------------------------------------------------------------------------------------+
```


TIME [ms]  12036.073664        ntokesn  1126  nchar  3372  :  10.689230607460035  [ms/tok]  3.5694168635824437  [ms/char]
TIME [ms]  10031.433235999999  ntokens  942  nchar  3071  :  10.64907986836518  [ms/tok]  3.266503821556496  [ms/char]



llama_print_timings:        load time =    1877.33 ms
llama_print_timings:      sample time =     298.91 ms /   943 runs   (    0.32 ms per token,  3154.76 tokens per second)
llama_print_timings: prompt eval time =     163.67 ms /   122 tokens (    1.34 ms per token,   745.39 tokens per second)
llama_print_timings:        eval time =    9496.45 ms /   942 runs   (   10.08 ms per token,    99.19 tokens per second)
llama_print_timings:       total time =   10014.35 ms /  1064 tokens