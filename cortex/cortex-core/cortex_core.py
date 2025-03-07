# cortex_core.py
import uuid
from litellm import completion
from notification_queue import notification_queue
from models import ConversationMessage


class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, user_id):
        session = {"user_id": user_id, "workspace": None}
        self.sessions[user_id] = session
        return session

    def get_session(self, user_id):
        return self.sessions.get(user_id)


class WorkspaceManager:
    def __init__(self):
        self.workspaces = {}

    def create_workspace(self, session, workspace_id):
        workspace = {"id": workspace_id, "conversation": []}
        session["workspace"] = workspace
        self.workspaces[workspace_id] = workspace
        return workspace

    def add_message(self, workspace, message):
        workspace["conversation"].append(message)

    def get_workspace(self, workspace_id):
        return self.workspaces.get(workspace_id)


class ContextManager:
    """
    A simple whiteboard memory model to store and update context.
    """

    def __init__(self):
        self.context = {}

    def update_context(self, workspace_id, new_context):
        if workspace_id not in self.context:
            self.context[workspace_id] = []
        self.context[workspace_id].append(new_context)

    def get_context(self, workspace_id):
        return self.context.get(workspace_id, [])


class Cognition:
    """
    Minimal adaptive reasoning.
    Now defaults to LLM integration for all inputs.
    """

    def process(self, input_text, context):
        # Always delegate to the domain expert (LLM integration is default)
        return {"delegate": True, "reason": "Defaulting to LLM integration"}


class DomainExpert:
    """
    A simplified domain expert that uses LiteLLM to call OpenAI's gpt-4o model in streaming mode.
    It iterates over the streaming response, prints each chunk, aggregates the text, and returns the final result.
    """

    def process(self, input_text, context):
        query = input_text.strip()
        try:
            stream = completion(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": query}],
                stream=True,
            )

            # Generate a single message id for the entire streaming sequence.
            message_id = str(uuid.uuid4())
            for chunk in stream:
                content = stream.response_uptil_now

                # Create a streaming conversation message with the same message id.
                msg = ConversationMessage(
                    message_id=message_id,
                    role="assistant",
                    content=content,
                    streaming=True,
                    metadata={},
                )
                try:
                    notification_queue.put_nowait(msg)
                except Exception as e:
                    print("Failed to push streaming message:", e)

            # After streaming is complete, send a final message.
            content = stream.response_uptil_now
            final_msg = ConversationMessage(
                message_id=message_id,
                role="assistant",
                content=content,
                streaming=False,
                metadata={},
            )
            try:
                notification_queue.put_nowait(final_msg)
            except Exception as e:
                print("Failed to push final message:", e)

            return stream.complete_response

        except Exception as e:
            error_msg = f"Error in DomainExpert: {str(e)}"
            print(error_msg)
            return error_msg


class Dispatcher:
    def __init__(self, cognition, domain_expert):
        self.cognition = cognition
        self.domain_expert = domain_expert

    def dispatch(self, input_text, context):
        decision = self.cognition.process(input_text, context)
        if decision.get("delegate"):
            return self.domain_expert.process(input_text, context)
        else:
            return decision.get("response")


class IntegrationHub:
    """
    Stub integration hub for output.
    It prints the output and pushes it to the global notification queue.
    Streaming chunks are already pushed by the DomainExpert.
    """

    def send_output(self, output_text):
        print("Output:", output_text)
        try:
            notification_queue.put_nowait(output_text)
        except Exception as e:
            print("Failed to push notification:", e)


class SecurityManager:
    """
    Minimal security manager that authenticates a user via a token.
    """

    def __init__(self):
        # Hardcoded token mapping for simplicity.
        self.valid_tokens = {"secret-token": "user1"}

    def authenticate(self, token):
        return self.valid_tokens.get(token)


class CortexCore:
    """
    The central Cortex Core that orchestrates sessions, context, cognition, and routing.
    """

    def __init__(self):
        self.session_manager = SessionManager()
        self.workspace_manager = WorkspaceManager()
        self.context_manager = ContextManager()
        self.cognition = Cognition()
        self.domain_expert = DomainExpert()
        self.dispatcher = Dispatcher(self.cognition, self.domain_expert)
        self.integration_hub = IntegrationHub()
        self.security_manager = SecurityManager()

    def process_input(self, user_id, input_text, token):
        # Authenticate the user.
        if not self.security_manager.authenticate(token):
            return "Authentication failed"

        # Retrieve or create a session.
        session = self.session_manager.get_session(user_id)
        if not session:
            session = self.session_manager.create_session(user_id)
            workspace = self.workspace_manager.create_workspace(
                session, f"{user_id}-ws"
            )
        else:
            workspace = session.get("workspace")
            if not workspace:
                workspace = self.workspace_manager.create_workspace(
                    session, f"{user_id}-ws"
                )

        # Log the input in the workspace conversation.
        self.workspace_manager.add_message(
            workspace, {"user": user_id, "text": input_text}
        )
        self.context_manager.update_context(workspace["id"], input_text)
        current_context = self.context_manager.get_context(workspace["id"])

        # Process the input (delegating to the LLM by default).
        response = self.dispatcher.dispatch(input_text, current_context)

        # Send the full response to the integration hub.
        self.integration_hub.send_output(response)

        # Log the response in the workspace.
        self.workspace_manager.add_message(
            workspace, {"assistant": "core", "text": response}
        )

        return response


if __name__ == "__main__":
    # Example usage:
    core = CortexCore()
    user_id = "user1"
    token = "secret-token"
    input_text = "Can you generate a friendly greeting?"
    response = core.process_input(user_id, input_text, token)
    print("Final Response:", response)
