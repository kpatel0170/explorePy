# UML Visualizer for Microservice Architecture

## Overview
This project provides a Python-based script that generates UML diagrams using PlantUML to visualize a microservice architecture. The tool processes data from multiple microservices and creates a structured diagram to represent their relationships and attributes. It is particularly useful for engineers working on microservices to understand dependencies and data flow.

## User Story
> As a software engineer, I want to know what microservice data will be used in the visualizer and how we will retrieve that data so that we can establish the input of the Python visualizer script.

## Features
- **Profile Microservice**: Visualizes user profile information.
- **Posts Management Microservice**: Displays posts, including captions, images, comments, and hashtags.
- **Moderation Microservice**: Highlights reported posts and moderation details.

## Installation

1. Clone this repository:
   ```bash
   git clone <repository_url>
   ```
2. Install required dependencies:
   ```bash
   uv sync
   ```
   
3. Ensure PlantUML is accessible for generating images. This script uses the public PlantUML server.

## Usage

### Input Data
Prepare JSON files for each microservice:
- **Profile Microservice** (`profile_service_response.json`): Contains user profile information.
- **Posts Management Microservice** (`posts_management_service_response.json`): Contains data about posts and comments.
- **Moderation Microservice** (`moderation_service_response.json`): Contains moderation information for posts.

Place these files in the `./files/` directory.

### Running the Script
Run the script to generate the UML diagram:
```bash
uv run python main.py
```

### Output
1. **PlantUML Text File**: Generated UML code is saved as `plantuml.txt`.
2. **UML Diagram**: An image is created using the PlantUML public server and saved in the same directory.

## Microservice Data Examples

### Profile Microservice
```json
{
  "name": "Kate",
  "username": "randomkate",
  "biography": "Software Engineer",
  "hyperlink": "linktr.ee/randomkate",
  "is_reported": true,
  "is_shadowbanned": false,
  "number_of_followers": 29048,
  "number_of_posts": 541,
  "number_of_following": 692
}
```

### Posts Management Microservice
```json
[
  {
    "posted_by": "randomkate",
    "post_caption": "ASCII is fun",
    "images": ["bit.ly/304qDIV", "bit.ly/3zRs8wQ"],
    "number_of_likes": 320,
    "comments": [
      {
        "username": "purplebytes",
        "comment": "Great post"
      }
    ],
    "hashtags": ["softwaredevelopment", "engineer", "tech"],
    "post_id": 1223,
    "date_published": "2023-03-20 16:34:04.862380"
  }
]
```

### Moderation Microservice
```json
{
  "post_id": 1223,
  "is_reported": true,
  "is_manual": true,
  "reason": "Used bad word",
  "post_caption": "ASCII is fun",
  "images": ["bit.ly/304qDIV", "bit.ly/3zRs8wQ"],
  "reported_by": "browniebits"
}
```

## How It Works
1. **Data Loading**: The script loads JSON data from the `./files/` directory.
2. **PlantUML File Generation**: Attributes and relationships are written to `plantuml.txt` using PlantUML syntax.
3. **Diagram Creation**: The script interacts with the PlantUML server to generate the UML diagram as an image.


## Contribution
Feel free to submit issues or pull requests to improve the functionality of this tool.

---

Happy diagramming!
