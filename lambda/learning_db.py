import boto3
import json
import decimal

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from datetime import datetime

class LearningDB():
    def __init__(self):
        self.create_textbook_table()
        self.create_learning_record_table()

    def create_textbook_table(self):
        TABLE_NAME = "ask.parrot_tutor.learning_db.textbook_table"
        
        dynamodb = boto3.resource('dynamodb')
        try:
            self.textbook_table = dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {
                        'AttributeName': 'user_id',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'heading',
                        'KeyType': 'RANGE'
                    }
                    ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'user_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'heading',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'learned_count',
                        'AttributeType': 'N'                        
                    }
                    ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                },
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'learned_count_index',
                        'KeySchema': [
                            {
                                'AttributeName': 'user_id',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'learned_count',
                                'KeyType': 'RANGE'
                            }
                            ],
                        'Projection': {
                            'ProjectionType': 'INCLUDE',
                            'NonKeyAttributes': [
                                'heading_type',
                                'learned_at',
                                'translation'
                                ]
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                    ]
                )
        except ClientError as e:
            self.textbook_table = dynamodb.Table(TABLE_NAME)
            
        # self.textbook_table.wait_until_exists()

    def create_learning_record_table(self):
        TABLE_NAME = "ask.parrot_tutor.learning_db.learning_record_table"
        
        dynamodb = boto3.resource('dynamodb')
        try:
            self.learning_record_table = dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {
                        'AttributeName': 'user_id',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'heading_type',
                        'KeyType': 'RANGE'
                    },
                    ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'user_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'heading_type',
                        'AttributeType': 'S'
                    }
                    ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
                )
        except ClientError as e:
            self.learning_record_table = dynamodb.Table(TABLE_NAME)
            
        # self.learning_record_table.wait_until_exists()
        
    def put_item(self, user_id, heading, heading_type, translation="", sequence=0, next_sequence=0):
        ts = decimal.Decimal(datetime.now().timestamp())
        item = {
                'user_id': user_id,
                'heading': heading,
                'created_at': ts,
                'updated_at': ts,
                'learned_at': ts,
                'learned_count': 0,
                'heading_type': heading_type,
                'translation': translation,
                'sequence': sequence,
                'next_sequence': next_sequence
            }
        self.textbook_table.put_item(
            Item=item
            )

    def query_item(self, user_id, heading_type, max_learned_count):
        response = self.textbook_table.query(
            IndexName="learned_count_index",
            KeyConditionExpression=Key('user_id').eq(user_id) & Key('learned_count').eq(max_learned_count),
            FilterExpression=Attr('heading_type').contains(heading_type)
            )
        
        return response['Items'] if response else []
        
    def get_max_learned_count(self, user_id, heading_type):
        try:
            response = self.learning_record_table.get_item(
                Key={
                    'user_id': user_id,
                    'heading_type': heading_type
                }
                )
            if 'Item' in response:
                return int(response['Item']['max_learned_count'])
            else:
                self.learning_record_table.put_item(
                    Item={
                        'user_id': user_id,
                        'heading_type': heading_type,
                        'max_learned_count': 0
                    })
                return 0
        except ClientError as e:
            return 0

    def increment_learned_count(self, user_id, heading):
        ts = decimal.Decimal(datetime.now().timestamp())
        response = self.textbook_table.update_item(
            Key={
                'user_id': user_id,
                'heading': heading
            },
            UpdateExpression='set learned_at=:learned_at, learned_count=learned_count + :one',
            ExpressionAttributeValues={
                ':learned_at': ts,
                ':one': 1
            },
            ReturnValues="UPDATED_NEW"
            )
        
    def update_max_learned_count(self, user_id, heading_type, count):
        response = self.learning_record_table.update_item(
            Key={
                'user_id': user_id,
                'heading_type': heading_type
            },
            UpdateExpression='set max_learned_count=:max_learned_count',
            ExpressionAttributeValues={
                ':max_learned_count': count
            },
            ReturnValues="UPDATED_NEW"
            )

