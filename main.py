import os
import json
import matplotlib.pyplot as plt
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import tiktoken

# Global variables for cost calculation (see https://openai.com/api/pricing/)
COST_INPUT_TOKEN = 5.0  # dollars per million tokens
COST_OUTPUT_TOKEN = 15.0  # dollars per million tokens
COST_BASE_IMAGE = 85  # tokens for each image
COST_IMAGE_TILE = 170  # tokens for each 512x512 tile in an image
MODEL = "gpt-4o"


def count_tokens(text, model=MODEL):
    """
    Count the number of tokens in a given text using the specified model's tokenizer.

    Args:
    text (str): The text to tokenize.
    model (str): The name of the model to use for tokenization. Default is "gpt-3.5-turbo-0613".

    Returns:
    int: The number of tokens in the text.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        if 'width' in text.keys() and 'height' in text.keys():
            return COST_BASE_IMAGE + COST_IMAGE_TILE * (text['width'] * text['height'] // (512 * 512))
        else:
            print(f"Error tokenizing text: {e}")
            return 0


def read_conversation_json(file_path):
    """Read and parse the JSON file containing the conversation data."""
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def extract_token_usage(data):
    """Extract the monthly token usage from the conversation data."""
    monthly_input_tokens = defaultdict(int)
    monthly_output_tokens = defaultdict(int)

    for conversation in data:
        for message_id, message_data in conversation['mapping'].items():
            try:
                message_content = message_data.get('message', {}).get('content', {}).get('parts', [''])
                author_role = message_data.get('message', {}).get('author', {}).get('role', '')
                create_time = message_data.get('message', {}).get('create_time')
                if create_time and message_content[0]:
                    month_key = datetime.fromtimestamp(create_time).strftime('%Y-%m')
                    for part in message_content:
                        token_count = count_tokens(part)
                        if author_role == 'user':
                            monthly_input_tokens[month_key] += token_count
                        elif author_role == 'assistant':
                            monthly_output_tokens[month_key] += token_count
            except AttributeError:
                pass
    return monthly_input_tokens, monthly_output_tokens


def get_all_months(start_date, end_date):
    """Generate a list of all months between start_date and end_date."""
    months = []
    current_date = start_date
    while current_date <= end_date:
        months.append(current_date.strftime('%Y-%m'))
        current_date += relativedelta(months=1)
    return months


def calculate_cost(input_tokens, output_tokens):
    """Calculate the cost based on input and output tokens."""
    return (input_tokens * COST_INPUT_TOKEN + output_tokens * COST_OUTPUT_TOKEN) / 1_000_000


def plot_token_usage(monthly_input_tokens, monthly_output_tokens):
    """Plot the monthly token usage and cumulative token usage as bar graphs with cost as line plots."""
    # Determine the date range
    all_dates = set(monthly_input_tokens.keys()) | set(monthly_output_tokens.keys())
    start_date = min(datetime.strptime(date, '%Y-%m') for date in all_dates)
    end_date = max(datetime.today(), max(datetime.strptime(date, '%Y-%m') for date in all_dates))

    # Get all months in the range
    all_months = get_all_months(start_date, end_date)

    # Prepare data for plotting
    input_data = [monthly_input_tokens.get(month, 0) for month in all_months]
    output_data = [monthly_output_tokens.get(month, 0) for month in all_months]

    # Calculate cumulative data
    cumulative_input = [sum(input_data[:i+1]) for i in range(len(input_data))]
    cumulative_output = [sum(output_data[:i+1]) for i in range(len(output_data))]

    # Calculate monthly and cumulative costs
    monthly_costs = [calculate_cost(input_data[i], output_data[i]) for i in range(len(input_data))]
    cumulative_costs = [sum(monthly_costs[:i+1]) for i in range(len(monthly_costs))]

    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    x = range(len(all_months))
    width = 0.35

    # Monthly usage plot
    ax1.bar([i - width/2 for i in x], input_data, width, label='Input Tokens', color='skyblue')
    ax1.bar([i + width/2 for i in x], output_data, width, label='Output Tokens', color='lightgreen')
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Token Count')
    ax1.set_title('Monthly Token Usage and Cost')
    ax1.set_xticks(x)
    ax1.set_xticklabels(all_months, rotation=45, ha='right')
    ax1.legend(loc='upper left')

    # Add cost line to monthly plot
    ax1_twin = ax1.twinx()
    ax1_twin.plot(x, monthly_costs, color='red', label='Monthly Cost', marker='o', alpha=0.5)
    ax1_twin.set_ylabel('Cost (USD)', color='red')
    ax1_twin.tick_params(axis='y', labelcolor='red')
    ax1_twin.legend(loc='upper right')

    # Cumulative usage plot
    ax2.bar([i - width/2 for i in x], cumulative_input, width, label='Cumulative Input Tokens', color='skyblue')
    ax2.bar([i + width/2 for i in x], cumulative_output, width, label='Cumulative Output Tokens', color='lightgreen')
    ax2.set_xlabel('Month')
    ax2.set_ylabel('Cumulative Token Count')
    ax2.set_title('Cumulative Token Usage and Cost')
    ax2.set_xticks(x)
    ax2.set_xticklabels(all_months, rotation=45, ha='right')
    ax2.legend(loc='upper left')

    # Add cost line to cumulative plot
    ax2_twin = ax2.twinx()
    ax2_twin.plot(x, cumulative_costs, color='red', label='Cumulative Cost', marker='o', alpha=0.5)
    ax2_twin.set_ylabel('Cumulative Cost (USD)', color='red')
    ax2_twin.tick_params(axis='y', labelcolor='red')
    ax2_twin.legend(loc='upper right')

    fig.suptitle('Monthly and Cumulative Token Usage with Cost')
    plt.tight_layout()
    plt.show()


def print_token_usage(monthly_input_tokens, monthly_output_tokens):
    """Print the monthly and cumulative token usage with cost."""
    # Determine the date range
    all_dates = set(monthly_input_tokens.keys()) | set(monthly_output_tokens.keys())
    start_date = min(datetime.strptime(date, '%Y-%m') for date in all_dates)
    end_date = max(datetime.today(), max(datetime.strptime(date, '%Y-%m') for date in all_dates))

    # Get all months in the range
    all_months = get_all_months(start_date, end_date)

    # Prepare data for printing
    input_data = [monthly_input_tokens.get(month, 0) for month in all_months]
    output_data = [monthly_output_tokens.get(month, 0) for month in all_months]

    # Calculate cumulative data
    cumulative_input = [sum(input_data[:i+1]) for i in range(len(input_data))]
    cumulative_output = [sum(output_data[:i+1]) for i in range(len(output_data))]

    # Calculate monthly and cumulative costs
    monthly_costs = [calculate_cost(input_data[i], output_data[i]) for i in range(len(input_data))]
    cumulative_costs = [sum(monthly_costs[:i+1]) for i in range(len(monthly_costs))]

    # Print the monthly and cumulative token usage with cost
    print(f'{"Month":<10}{"Input Tokens":>15}{"Output Tokens":>15}{"Cost (USD)":>15}')
    for i in range(len(all_months)):
        print(f'{all_months[i]:<10}{input_data[i]:>15,}{output_data[i]:>15,}{monthly_costs[i]:>15,.2f}')
    print()
    print(f'{"Month":<10}{"Cumulative Input Tokens":>15}{"Cumulative Output Tokens":>15}{"Cumulative Cost (USD)":>15}')
    for i in range(len(all_months)):
        print(f'{all_months[i]:<10}{cumulative_input[i]:>15,}{cumulative_output[i]:>15,}{cumulative_costs[i]:>15,.2f}')


def main():
    # Define the path to the JSON file
    json_file_path = './conversation/conversations.json'

    # Read and parse the JSON file
    data = read_conversation_json(json_file_path)

    # Extract the monthly token usage
    monthly_input_tokens, monthly_output_tokens = extract_token_usage(data)

    # Print the monthly and cumulative token usage with cost
    print_token_usage(monthly_input_tokens, monthly_output_tokens)

    # Plot the monthly and cumulative token usage with cost
    plot_token_usage(monthly_input_tokens, monthly_output_tokens)


if __name__ == '__main__':
    main()