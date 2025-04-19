import concurrent.futures
from class_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables

def process_text_chunk(text_chunk, genre="prose", debug=True):
    """Process a chunk of text with the Macronizer."""
    macronizer = Macronizer(debug=debug)
    output = macronizer.macronize(text=text_chunk, genre=genre, stats=True)
    return output

def parallel_macronize(text, genre="prose", debug=True):
    """Macronize text in parallel using two workers."""
    # Split the text into two parts at roughly the middle
    midpoint = len(text) // 2
    
    # Find the nearest period to the midpoint to avoid breaking sentences
    split_point = text.find(".", midpoint)
    if split_point == -1:  # If no period found after midpoint, look before
        split_point = text.rfind(".", 0, midpoint)
    if split_point == -1:  # If still no period found, just use midpoint
        split_point = midpoint
    else:
        split_point += 1  # Include the period in the first part
    
    first_half = text[:split_point]
    second_half = text[split_point:]
    
    # Process the two parts in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        future_to_text = {
            executor.submit(process_text_chunk, first_half, genre, debug): "first",
            executor.submit(process_text_chunk, second_half, genre, debug): "second"
        }
        
        results = {"first": "", "second": ""}
        for future in concurrent.futures.as_completed(future_to_text):
            part = future_to_text[future]
            try:
                results[part] = future.result()
            except Exception as e:
                print(f"Error processing {part} part: {e}")
    
    # Combine the results
    return results["first"] + results["second"]

# Example usage
if __name__ == "__main__":
    #from tests.tragedies import tragedies
    from tests.anabasis import anabasis
    
    input = anabasis

    print("Processing text in parallel...")
    output = parallel_macronize(input)
    
    print("Displaying results:")
    for line in output.split('.')[:10]:
        print(colour_dichrona_in_open_syllables(line))