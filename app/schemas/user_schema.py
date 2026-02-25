from marshmallow import Schema, fields, validate, validates, ValidationError
from datetime import date

class UserCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    password = fields.Str(required=True, validate=validate.Length(min=6))
    dob = fields.Date(required=False)
    gender = fields.Str(validate=validate.OneOf(["male", "female", "other", 'prefer-not-to-say']))
    email = fields.Email(required=True)
    ai_preferences = fields.Dict(required=False)
    status = fields.Str(validate=validate.OneOf(["active", "inactive"]))

    @validates("dob")
    def validate_dob(self, value, **kwargs):
        if value and value > date.today():
            raise ValidationError("Date of birth cannot be in the future.")

class UserStatusSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(["active", "inactive"]))

class UserUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=100))
    dob = fields.Date(required=False)
    gender = fields.Str(validate=validate.OneOf(["male", "female", "other"]))
    email = fields.Email(required=False)
    ai_preferences = fields.Dict(required=False)
    status = fields.Str(validate=validate.OneOf(["active", "inactive"]))

    @validates("dob")
    def validate_dob(self, value, **kwargs):
        if value and value > date.today():
            raise ValidationError("Date of birth cannot be in the future.")

