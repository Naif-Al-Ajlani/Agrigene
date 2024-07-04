import streamlit as st
import requests
import json
from PIL import Image
import base64
import re
import os
from inference_sdk import InferenceHTTPClient

# Roboflow Client Setup
CLIENT = InferenceHTTPClient(
    api_url="https://classify.roboflow.com",
    api_key="iTFKPbg4Ent4LB4xcaQu"
)

# Function to call the Plant.id API for plant identification
def identify_plant(image_path):
    url = "https://plant.id/api/v3/identification"

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    payload = json.dumps({
        "images": [image_base64],
        "latitude": 49.207,
        "longitude": 16.608,
        "similar_images": True
    })
    headers = {
        'Api-Key': 'sCTfpZXoHBxVdfjRd8GCIpRPCX8wga7txv7s4XBVpvQkZvvpF8',
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)
    return response.text

# Function to call the Plant.id API for plant health assessment
def check_plant_health(image_path):
    url = "https://plant.id/api/v3/health_assessment?details=local_name,description,url,treatment,classification,common_names,cause"

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    payload = json.dumps({
        "images": [image_base64],
        "latitude": 49.207,
        "longitude": 16.608,
        "similar_images": True
    })
    headers = {
        'Api-Key': 'sCTfpZXoHBxVdfjRd8GCIpRPCX8wga7txv7s4XBVpvQkZvvpF8',
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)
    return response.text

# Function to convert scientific name to common name
def scientific_2_common_name(scientific_name):
    with open('plants.json', 'r') as file:
        data = json.load(file)

    for plant in data['plants']:
        species_trimmed = re.sub(r'[^a-zA-Z]', '', plant['species']).lower()
        scientific_name_trimmed = re.sub(r'[^a-zA-Z]', '', scientific_name).lower()
        
        if species_trimmed == scientific_name_trimmed:
            return plant['name']
    return scientific_name

# Function to identify soil using Roboflow
def identify_soil(image_path):
    result = CLIENT.infer(image_path, model_id="soil-classification-07l98/1")
    soil_predictions = [
        f"It is {prediction['class']} with Confidence of {prediction['confidence'] * 100}%"
        for prediction in result['predictions']
    ]
    return soil_predictions

# Custom CSS for background and styling
st.markdown("""
    <style>
    body {
        background-image: url("https://st.depositphotos.com/1033604/2008/i/450/depositphotos_20087015-stock-photo-sunlit-young-corn-plants.jpg");
        background-size: cover;
    }
    .main {
        background: rgba(255, 255, 255, 0.8);
        border-radius: 10px;
        padding: 20px;
    }
    .stButton > button {
        display: inline-block;
        margin-right: 10px;
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        font-size: 16px;
        border-radius: 5px;
    }
    .stButton > button:hover {
        background-color: #45a049;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='main'>", unsafe_allow_html=True)
st.title("Gardening Assistant")
st.markdown("<hr>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Uploaded Image.', use_column_width=True)
    st.write("")

    temp_image_path = "temp_image.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button('Identify Plant'):
            st.write("Classifying...")
            result = identify_plant(temp_image_path)
            try:
                data = json.loads(result)
                plant_name = data['result']['classification']['suggestions'][0]['name']
                probability_of_plant = data['result']['classification']['suggestions'][0]['probability']
                common_name = scientific_2_common_name(plant_name)
                st.write(f"This is {common_name} and has a probability of {probability_of_plant}")
            except json.JSONDecodeError:
                st.error("Failed to decode the API response as JSON.")
                st.write(result)
            except KeyError:
                st.error("Unexpected response structure received from the API.")
                st.write(result)

    with col2:
        if st.button('Check Plant Health'):
            st.subheader("Assessing health...")
            result = check_plant_health(temp_image_path)
            try:
                result = json.loads(result)

                if "result" in result:
                    extracted_info = {
                        "is_healthy": result["result"]["is_healthy"]["binary"],
                        "is_plant": result["result"]["is_plant"]["binary"],
                        "suggestions": [
                            {
                                "id": suggestion["id"],
                                "name": suggestion["name"],
                                "probability": suggestion["probability"],
                                "similar_images": [
                                    {
                                        "similarity": data["similarity"],
                                        'url': data["url"]
                                    } 
                                    for data in suggestion["similar_images"]
                                ],
                                "treatment": suggestion["details"]["treatment"] if "details" in suggestion and "treatment" in suggestion["details"] else None
                            }
                            for suggestion in result["result"]["disease"]["suggestions"]
                        ],
                    }

                    if extracted_info["is_healthy"]:
                        st.markdown("<p style='color:green; font-weight: bold;'>This plant looks healthy</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color:red; font-weight: bold;'>The plant is not healthy</p>", unsafe_allow_html=True)

                    if not extracted_info["is_plant"]:
                        st.write("It looks like there is no plant in the picture.")

                    st.markdown("\n**Probable Diseases**")
                    for suggestion in extracted_info["suggestions"]:
                        if float(suggestion["probability"]) > 0.7:
                            st.markdown(f"**It has {suggestion['name']} with Probability of {suggestion['probability']*100:.2f}%**")
                            
                            if suggestion["treatment"]:
                                st.subheader("Treatments:")
                                if "chemical" in suggestion["treatment"]:
                                    st.write("**Chemical Treatments:**")
                                    for treatment in suggestion["treatment"]["chemical"]:
                                        st.write(f"{treatment}")
                                if "biological" in suggestion["treatment"]:
                                    st.write("**Biological Treatments:**")
                                    for treatment in suggestion["treatment"]["biological"]:
                                        st.write(f"{treatment}")
                                if "prevention" in suggestion["treatment"]:
                                    st.write("**Prevention Methods**")
                                    for treatment in suggestion["treatment"]["prevention"]:
                                        st.write(f"{treatment}")

                    st.subheader("Similar Images")
                    for suggestion in extracted_info["suggestions"]:
                        for similarity in suggestion['similar_images']:
                            if similarity["similarity"] > 0.6:
                                st.image(similarity["url"], caption=f"Similarity: {similarity['similarity']:.2f}", width=100)
            except json.JSONDecodeError:
                st.error("Failed to decode the API response as JSON")
                st.write(result)
            except KeyError:
                st.error("Unexpected response structure received from the API.")
                st.write(result)

    with col3:
        if st.button('Identify Soil'):
            st.write("Identifying soil type...")
            soil_predictions = identify_soil(temp_image_path)
            for prediction in soil_predictions:
                st.write(prediction)

st.markdown("</div>", unsafe_allow_html=True)
