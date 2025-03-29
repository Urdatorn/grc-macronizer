import os
import openai

api_key = os.getenv("MY_API_KEY") # export MY_API_KEY="your-key-here"
openai.api_key = api_key

def lemma_generalization(self, macronized_token, lemma):
    """
    Queries a fine-tuned ChatGPT model to generalize a macronized token based on its lemma.
    
    Args:
        macronized_token (str): The macronized token (e.g., "ābc").
        lemma (str): The lemma of the token (e.g., "abc").
    
    Returns:
        str: The generalized output from the model.
    """
    # Craft a prompt for the model
    prompt = f"Given a macronized token '{macronized_token}' and its lemma '{lemma}', provide the generalized form."
    
    try:
        # Query the fine-tuned model
        response = openai.ChatCompletion.create(
            model="your-finetuned-model-id",  # Replace with your fine-tuned model ID
            messages=[
                {"role": "system", "content": "You are a linguistic expert specializing in lemma generalization."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,  # Adjust based on expected response length
            temperature=0.5  # Adjust for creativity vs. determinism
        )
        
        # Extract and return the model's response
        generalized_form = response.choices[0].message['content'].strip()
        return generalized_form
    
    except Exception as e:
        print(f"Error querying model: {e}")
        # Fallback to original token if the API call fails
        return macronized_token
