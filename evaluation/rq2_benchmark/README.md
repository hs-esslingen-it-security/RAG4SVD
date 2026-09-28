# RQ2 — Unified Benchmark

This directory contains the artifacts for **RQ2: How do open-source RAG4SVD systems compare under a unified benchmark?**

We evaluate the considered RAG4SVD systems on the common **PrimeVul Paired** benchmark using a shared pool of open-weight backbone models. The PrimeVul training split is used as the basis for system-specific retrieval knowledge, while the test split is used for detection.

We report:

- **Pairwise Accuracy** — a pair is correct only if the vulnerable function is predicted as vulnerable and its corresponding patch as non-vulnerable.
- **F1** — standard vulnerable-class F1 score.
- **% Parsed** — fraction of vulnerability–patch pairs for which both predictions could be parsed successfully.

Detection metrics are reported only for configurations with at least **95% parseable predictions**. Parsing success is reported for all configurations to make differences in output-format robustness visible.


## Results
Results are reported to three decimal places to expose differences between configurations that are rounded in the paper. Detection metrics are omitted (`—`) when fewer than 95% of vulnerability–patch pairs yield parseable predictions.


<table>
  <thead>
    <tr>
      <th></th>
      <th colspan="3">SVD-Bench</th>
      <th colspan="3">GRACE</th>
      <th colspan="3">Llama-VD</th>
      <th colspan="3">Vul-RAG</th>
      <th colspan="3">VulTriage</th>
    </tr>
    <tr>
      <th>Model</th>
      <th>Pair. Acc.</th>
      <th>F1</th>
      <th>%parsed</th>
      <th>Pair. Acc.</th>
      <th>F1</th>
      <th>%parsed</th>
      <th>Pair. Acc.</th>
      <th>F1</th>
      <th>%parsed</th>
      <th>Pair. Acc.</th>
      <th>F1</th>
      <th>%parsed</th>
      <th>Pair. Acc.</th>
      <th>F1</th>
      <th>%parsed</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>qwen2.5-coder-3b-instruct</td>
      <td>0.073</td><td>0.333</td><td>0.995</td>
      <td>0.044</td><td>0.621</td><td>1.000</td>
      <td>0.069</td><td>0.450</td><td>0.987</td>
      <td>—</td><td>—</td><td>0.092</td>
      <td>—</td><td>—</td><td>0.830</td>
    </tr>
    <tr>
      <td>qwen2.5-coder-14b-instruct</td>
      <td>0.087</td><td>0.482</td><td>0.999</td>
      <td>0.021</td><td>0.391</td><td>1.000</td>
      <td>0.071</td><td>0.460</td><td>0.999</td>
      <td>0.217</td><td>0.554</td><td>1.000</td>
      <td>0.072</td><td>0.141</td><td>0.990</td>
    </tr>
    <tr>
      <td>qwen2.5-coder-32b-instruct</td>
      <td>0.087</td><td>0.431</td><td>0.995</td>
      <td>0.035</td><td>0.387</td><td>1.000</td>
      <td>0.108</td><td>0.480</td><td>0.993</td>
      <td>0.165</td><td>0.533</td><td>1.000</td>
      <td>0.209</td><td>0.369</td><td>0.990</td>
    </tr>
    <tr>
      <td>qwen2.5-3b-instruct</td>
      <td>0.126</td><td>0.492</td><td>0.969</td>
      <td>0.095</td><td>0.560</td><td>1.000</td>
      <td>0.099</td><td>0.460</td><td>0.994</td>
      <td>0.120</td><td>0.506</td><td>0.998</td>
      <td>—</td><td>—</td><td>0.020</td>
    </tr>
    <tr>
      <td>qwen2.5-14b-instruct</td>
      <td>0.128</td><td>0.528</td><td>0.994</td>
      <td>0.039</td><td>0.459</td><td>1.000</td>
      <td>0.090</td><td>0.490</td><td>0.999</td>
      <td>0.184</td><td>0.554</td><td>1.000</td>
      <td>—</td><td>—</td><td>0.580</td>
    </tr>
    <tr>
      <td>qwen2.5-32b-instruct</td>
      <td>0.119</td><td>0.560</td><td>0.990</td>
      <td>0.030</td><td>0.441</td><td>1.000</td>
      <td>0.129</td><td>0.480</td><td>0.993</td>
      <td>0.155</td><td>0.557</td><td>1.000</td>
      <td>—</td><td>—</td><td>0.860</td>
    </tr>
    <tr>
      <td>qwen3-4b-instruct</td>
      <td>0.099</td><td>0.466</td><td>0.991</td>
      <td>0.097</td><td>0.262</td><td>0.987</td>
      <td>0.094</td><td>0.470</td><td>0.994</td>
      <td>0.169</td><td>0.541</td><td>1.000</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>qwen3.5-9b</td>
      <td>—</td><td>—</td><td>0.875</td>
      <td>0.051</td><td>0.169</td><td>0.957</td>
      <td>0.154</td><td>0.500</td><td>0.994</td>
      <td>—</td><td>—</td><td>—</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>qwen3.6-27b</td>
      <td>—</td><td>—</td><td>0.066</td>
      <td>0.007</td><td>0.014</td><td>1.000</td>
      <td>0.064</td><td>0.420</td><td>0.983</td>
      <td>0.137</td><td>0.559</td><td>0.982</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>qwq-32b</td>
      <td>0.119</td><td>0.576</td><td>0.943</td>
      <td>0.171</td><td>0.623</td><td>0.970</td>
      <td>0.055</td><td>0.430</td><td>0.994</td>
      <td>0.210</td><td>0.568</td><td>0.977</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>llama3.2-3b-instruct</td>
      <td>0.094</td><td>0.366</td><td>1.000</td>
      <td>0.005</td><td>0.667</td><td>0.982</td>
      <td>0.115</td><td>0.480</td><td>0.995</td>
      <td>—</td><td>—</td><td>0.847</td>
      <td>—</td><td>—</td><td>0.060</td>
    </tr>
    <tr>
      <td>llama3.1-8b-instruct</td>
      <td>0.119</td><td>0.459</td><td>1.000</td>
      <td>0.000</td><td>0.667</td><td>1.000</td>
      <td>0.117</td><td>0.490</td><td>0.993</td>
      <td>0.120</td><td>0.530</td><td>1.000</td>
      <td>—</td><td>—</td><td>0.070</td>
    </tr>
    <tr>
      <td>phi-4-mini-instruct</td>
      <td>0.114</td><td>0.510</td><td>0.999</td>
      <td>0.086</td><td>0.549</td><td>0.972</td>
      <td>0.087</td><td>0.460</td><td>0.993</td>
      <td>—</td><td>—</td><td>0.850</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>phi-4</td>
      <td>0.097</td><td>0.358</td><td>0.999</td>
      <td>0.037</td><td>0.419</td><td>1.000</td>
      <td>0.110</td><td>0.490</td><td>0.997</td>
      <td>0.144</td><td>0.564</td><td>0.984</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>gemma-3-4b-it</td>
      <td>0.104</td><td>0.475</td><td>0.992</td>
      <td>0.069</td><td>0.639</td><td>1.000</td>
      <td>0.147</td><td>0.510</td><td>0.992</td>
      <td>0.186</td><td>0.504</td><td>0.982</td>
      <td>—</td><td>—</td><td>0.800</td>
    </tr>
    <tr>
      <td>gemma-3-12b-it</td>
      <td>0.078</td><td>0.357</td><td>1.000</td>
      <td>0.042</td><td>0.487</td><td>1.000</td>
      <td>0.085</td><td>0.480</td><td>0.994</td>
      <td>0.198</td><td>0.542</td><td>0.982</td>
      <td>0.062</td><td>0.634</td><td>1.000</td>
    </tr>
    <tr>
      <td>gemma-3-27b-it</td>
      <td>0.070</td><td>0.375</td><td>1.000</td>
      <td>0.035</td><td>0.578</td><td>1.000</td>
      <td>0.083</td><td>0.480</td><td>0.994</td>
      <td>0.195</td><td>0.552</td><td>0.982</td>
      <td>0.209</td><td>0.703</td><td>1.000</td>
    </tr>
    <tr>
      <td>nextcoder-14b</td>
      <td>0.075</td><td>0.426</td><td>0.998</td>
      <td>0.023</td><td>0.398</td><td>1.000</td>
      <td>0.069</td><td>0.460</td><td>0.999</td>
      <td>0.219</td><td>0.564</td><td>1.000</td>
      <td>0.065</td><td>0.129</td><td>0.990</td>
    </tr>
    <tr>
      <td>nextcoder-32b</td>
      <td>0.121</td><td>0.509</td><td>0.994</td>
      <td>0.062</td><td>0.405</td><td>1.000</td>
      <td>0.074</td><td>0.480</td><td>0.999</td>
      <td>0.187</td><td>0.552</td><td>0.993</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>deepseek-r1-8b</td>
      <td>0.119</td><td>0.480</td><td>0.997</td>
      <td>0.141</td><td>0.579</td><td>0.997</td>
      <td>0.094</td><td>0.460</td><td>0.993</td>
      <td>0.207</td><td>0.514</td><td>1.000</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>deepseek-r1-32b</td>
      <td>0.099</td><td>0.495</td><td>1.000</td>
      <td>0.155</td><td>0.507</td><td>0.997</td>
      <td>0.101</td><td>0.490</td><td>0.999</td>
      <td>0.193</td><td>0.532</td><td>1.000</td>
      <td>—</td><td>—</td><td>0.000</td>
    </tr>
    <tr>
      <td>mistral-7b-instruct-v0.3</td>
      <td>0.094</td><td>0.409</td><td>1.000</td>
      <td>0.055</td><td>0.569</td><td>0.993</td>
      <td>0.138</td><td>0.490</td><td>0.993</td>
      <td>—</td><td>—</td><td>0.899</td>
      <td>—</td><td>—</td><td>0.100</td>
    </tr>
  </tbody>
</table>


<br>


### Repeated Inference Runs

To assess run-to-run variability, we repeat (the strongest) configuration of each system three times and report the mean and standard deviation of Pairwise Accuracy.

| Best configuration | r1 | r2 | r3 | Mean | Std. |
|---|---:|---:|---:|---:|---:|
| SVD-Bench with `qwen2.5-14b-instruct` | 0.128 | 0.119 | 0.119 | 0.122 | 0.005 |
| GRACE with `qwq-32b` | 0.171 | 0.171 | 0.171 | 0.171 | 0.000 |
| Llama-VD with `qwen3.5-9b` | 0.154 | 0.154 | 0.154 | 0.154 | 0.000 |
| Vul-RAG with `qwen2.5-coder-14b-instruct` | 0.217 | **0.228** | 0.202 | 0.216 | 0.013 |
| VulTriage with `qwen2.5-coder-32b-instruct` | 0.209 | 0.209 | 0.209 | 0.209 | 0.000 |