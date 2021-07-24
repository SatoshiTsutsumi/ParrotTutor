# -*- coding: utf-8 -*-
import boto3
import decimal
import learning_db
import logging
import random
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = "Welcome, I can help you remember words or phrases. Please ask me to add what you want to remember."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class AddIntentHandler(AbstractRequestHandler):
    def __init__(self, heading_type):
        self.heading_type = heading_type
    
    """Handler for Add Item Intent."""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name(f"Add{self.heading_type}Intent")(handler_input)

    def handle(self, handler_input):
        global db, translate
        user_id = ask_utils.get_user_id(handler_input)
        locale = ask_utils.get_locale(handler_input)
        heading = ask_utils.get_slot_value(handler_input, f"{self.heading_type.lower()}Slot")
        
        response = translate.translate_text(
            Text=heading,
            SourceLanguageCode="en",
            TargetLanguageCode="ja"
        )
        translation = response['TranslatedText']
        db.put_item(user_id, heading, self.heading_type.upper(), translation=translation, sequence=0, next_sequence=0)
        
        translation_output = f"<voice name=\"Joanna\"><lang xml:lang=\"ja-JP\">{translation}</lang></voice>"
        speak_output = f"I remember the {self.heading_type}, {heading}, which means {translation_output}."
        reprompt = "Add another item or learn to memorize?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt)
                .response
        )

class LearnIntentHandler(AbstractRequestHandler):
    """Handler for Learn Intent."""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("LearnIntent")(handler_input)

    def handle(self, handler_input):
        global db
        user_id = ask_utils.get_user_id(handler_input)
        count_slot = ask_utils.get_slot_value(handler_input, "countSlot")
        count = int(count_slot) if count_slot is not None else 3
        heading_type_slot = ask_utils.get_slot_value(handler_input, "headingTypeSlot")
        heading_type = "word" if heading_type_slot == "words" else "phrase"
        heading_type_keyword = heading_type.upper()
        
        max_learned_count = db.get_max_learned_count(user_id, heading_type_keyword)
        filtered_items = []
        for learned_count in range(max_learned_count + 1):
            items = db.query_item(user_id, heading_type_keyword, learned_count)
            filtered_items.extend(random.sample(items, len(items)))
            if len(filtered_items) > count:
                break
        
        total = min(count, len(filtered_items))
        outputs = []
        for item in filtered_items[0:total]:
            heading = item['heading']
            translation = f"<voice name=\"Joanna\"><lang xml:lang=\"ja-JP\">{item['translation']}</lang></voice>"
            outputs.append(f"{heading}. {translation}")
            
            if item['learned_count'] >= max_learned_count:
                max_learned_count = item['learned_count'] + 1
            db.increment_learned_count(user_id, heading)
            
        
        
        if total > 0:
            db.update_max_learned_count(user_id, heading_type_keyword, max_learned_count)
            plural = "s" if total > 1 else ""
            if total != count:
                speak_output = f"You've added only {total} {heading_type}{plural}. " + ". ".join(outputs)
            else:
                speak_output = f"Let's learn {total} {heading_type}{plural}. " + ". ".join(outputs)
        else:
            speak_output = f"You haven't added any {heading_type} yet."
            
        reprompt = "Add another item or learn to memorize?"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt)
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "You can say add a word something or add a phrase something or learn words or learn phrases. What would you like to do?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Add, Learn, or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # Clean up logic here.
        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

db = learning_db.LearningDB()
sb = SkillBuilder()
translate = boto3.client(service_name='translate', region_name='us-west-1', use_ssl=True)

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AddIntentHandler("Word"))
sb.add_request_handler(AddIntentHandler("Phrase"))
sb.add_request_handler(LearnIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
sb.add_request_handler(IntentReflectorHandler()) 
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()

