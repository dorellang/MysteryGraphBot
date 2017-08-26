class SchemaLoadError(ValueError):
    def __init__(self, schema_cls, errors):
        msg = "Error when deserializing data from schema '{}'."
        msg = msg.format(str(schema_cls))
        super().__init__(self, msg)
        self.schema_cls = schema_cls
        self.errors = errors
