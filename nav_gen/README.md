# NavGen

### Introduction

The NavGen pipeline consists of four steps: generating the LH-VLN task config, recording trajectories, decomposing trajectories, and generating step-by-step tasks. These correspond to `gen_task`, `gen_traj`, `split_traj`, and `gen_step_task` in `main.py`, respectively.

We use GPT as the open-source large model, so please prepare your OpenAI API key in advance. You can replace the model used (default is GPT-4o mini, with an optional GPT-4o) in `task_gen.py` and `split_task.py`.

Although the entire NavGen pipeline is run at once in `main.py`, due to considerations regarding network connectivity and the stability of large model outputs, we recommend running the code step by step in sequence.

### Start

Before you start generating, I would like to introduce some important parameters.

- API_KEY: Your API key, used to call the GPT model. For the complete generation process of a task, it costs about 2000 tokens.
- loop: The number of cycles of the first step(generating LH-VLN task). This depends on how many tasks you want to generate.
- sample_region: Whether to sample rooms based on the Euler distance between rooms. Since the Euler distance cannot well represent the actual distance between rooms, it is set to **False** by default.
- sample_obj: Whether to randomly sample objects in the room. Since this can reduce the influence of large model preference selection, it is set to **True** by default.
- max_step: The maximum number of action steps in the second step(record the trajectory). Used to limit the trajectory that is too long. The default setting is **500**.
- ram_logs: The log save path of step 3 and step 4. This can help you confirm the actual progress of the NavGen.

These parameters can be viewed in `main.py`.

Now you can generate tasks with the following command:

```bash
cd nav_gen
python main.py --API_KEY <your_openai_api_key> --loop 100
```

Note: Due to factors such as navigation path obstruction, not all tasks generated in the first step can successfully record trajectories in the second step. For these tasks, after the second step trajectory generation is completed, the task directory will not contain a 'success' folder, but a 'tmp' folder instead. You can either delete them directly or resample the navigation starting points. The default navigation starting point is [randomly sampled from the navigable area](https://github.com/HCPLab-SYSU/LH-VLN/blob/4bf526a0518308d2b3030c9fb411e377267f5a2a/nav_gen/habitat_base/simulation.py#L43).
