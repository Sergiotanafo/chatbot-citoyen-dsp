"""
Generated or fallback Python gRPC service definitions for proto/dsp_service.proto.
Fournit le servicer et les stubs de communication gRPC pour le backend FastAPI.
"""

from typing import Any


class DspServiceServicer:
    """Interface abstraite pour le service DSP gRPC."""

    def PredictIntent(self, request, context):
        raise NotImplementedError("Method not implemented!")

    def SearchKnowledge(self, request, context):
        raise NotImplementedError("Method not implemented!")

    def TranscribeAudio(self, request, context):
        raise NotImplementedError("Method not implemented!")

    def SynthesizeSpeech(self, request, context):
        raise NotImplementedError("Method not implemented!")


def add_DspServiceServicer_to_server(servicer, server):
    """Enregistre le servicer sur le serveur gRPC (standard ou adaptateur)."""
    rpc_method_handlers = {
        "PredictIntent": servicer.PredictIntent,
        "SearchKnowledge": servicer.SearchKnowledge,
        "TranscribeAudio": servicer.TranscribeAudio,
        "SynthesizeSpeech": servicer.SynthesizeSpeech,
    }
    if hasattr(server, "add_generic_rpc_handlers"):
        try:
            import grpc
            # Enregistrement standard gRPC si dispo
            handler = grpc.method_handlers_generic_handler("dsp.DspService", rpc_method_handlers)
            server.add_generic_rpc_handlers((handler,))
        except Exception:
            pass
    setattr(server, "_dsp_servicer", servicer)
