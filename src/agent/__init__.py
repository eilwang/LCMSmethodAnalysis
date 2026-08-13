# Agent package for LCMS method optimization

"""
Usage Example:
--------------
from agent.tool_wrappers import parse_lc_method, parse_ms_method, load_diann_results
from agent.optuna_optimizer import LCMSOptimizer
from agent.claude_agent import ClaudeAgent

# Parse LC method
lc_info = parse_lc_method("path/to/lc_method.meth")
print(lc_info)

# Parse MS method
ms_info = parse_ms_method("path/to/ms_method.meth")
print(ms_info)

# Load DIA-NN results
results = load_diann_results("path/to/diann_results.zip", level="precursor")
print(results)

# Set up optimizer (define your own objective and param_space)
# optimizer = LCMSOptimizer(objective_func, param_space)
# best_params, best_score = optimizer.suggest(n_trials=20)

# Set up Claude agent (implement Claude API call in claude_agent.py)
# claude = ClaudeAgent(api_key="your_api_key")
# response = claude.ask("Suggest LCMS parameters", tools={...})
"""
