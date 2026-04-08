 We are going to build a tutor chat agent.
 The agent will help students understand lessons on Langchain, Langgraph, and Langsmith. It will be useful both as a tutor and as a coding example. The code to implement the agent will also be used as the subject of lessons.
 
 The agent can be invoked via a UI or individual calls.
 ## UI
 ### General layout
   The UI will have a graphic area at the top and a chat area at the bottom. The initial version is in langgraph_interactive.html.
   There will be tabs for different lessons. We'll start with 3 lessons, but this will grow. Only lesson 1 will be populated to start. Each lesson has a graphic area and a text area.
 
### The graphic area
    The graphics will be interactive, as shown in langgraph_interactive.html. There will be different interactive maps, so we will select them via tabs. As in the first example, clicking on sections will send a predefined question to the tutor agent, who will respond in the chat area.

## The agent

### The librarys
The agent will use the langgraph deepagent library (uv add deepagent). It will have an MCP server that talks to the langchain MCP docs server; instructions are here: https://docs.langchain.com/use-these-docs. 

### The data sources

#### Local Lesson data
There are local sources of information in lesson_x directories, where each lesson directory contains documents related to that lesson.
- lessonx_instructions.md that contains instructions on how the lesson should be run.
- lesson_x_information.md that contains lesson content. This is information that can be used to respond to questions (along with the mcp server) and information a student can be quizzed on.

#### 
The agent will be used locally via Langraph Studio and also deployed to Langraph Cloud.
  
Each tab will be a different langsmith assistant (https://docs.langchain.com/langsmith/assistants). Within a tab, users can create a new threads that represent different threads of a conversation.


## Lessons
