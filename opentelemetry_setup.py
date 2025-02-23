from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import openai

# Configure OpenTelemetry Tracer Provider with Jaeger Exporter
resource = Resource.create({"service.name": "knowledge-nexus-app"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument outgoing HTTP requests
RequestsInstrumentor().instrument()

# Patch openai.ChatCompletion.create to add a tracing span
_original_chat_completion_create = openai.ChatCompletion.create

def instrumented_chat_completion_create(*args, **kwargs):
    with tracer.start_as_current_span("OpenAI.ChatCompletion.create"):
        return _original_chat_completion_create(*args, **kwargs)

openai.ChatCompletion.create = instrumented_chat_completion_create

# Patch openai.Completion.create to add a tracing span
_original_completion_create = openai.Completion.create

def instrumented_completion_create(*args, **kwargs):
    with tracer.start_as_current_span("OpenAI.Completion.create"):
        return _original_completion_create(*args, **kwargs)

openai.Completion.create = instrumented_completion_create

# Patch openai.Embedding.create to add a tracing span, if available
if hasattr(openai, "Embedding") and hasattr(openai.Embedding, "create"):
    _original_embedding_create = openai.Embedding.create
    def instrumented_embedding_create(*args, **kwargs):
        with tracer.start_as_current_span("OpenAI.Embedding.create"):
            return _original_embedding_create(*args, **kwargs)
    openai.Embedding.create = instrumented_embedding_create 