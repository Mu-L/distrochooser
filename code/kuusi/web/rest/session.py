"""
distrochooser
Copyright (C) 2014-2025  Christoph Müller  <mail@chmr.eu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from typing import Dict, Any

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from kuusi.settings import (
    FRONTEND_URL,
    KUUSI_ICON,
    KUUSI_LOGO,
    KUUSI_META_TAGS,
    KUUSI_NAME,
    AVAILABLE_LANGUAGES,
    RTL_LANGUAGES,
    SESSION_NUMBER_OFFSET,
    IMPRINT,
    PRIVACY,
    DEFAULT_LANGUAGE_CODE,
    ENABLE_TRANSLATION_MODE,
    ENABLE_FEEDBACK_MODE,
)
from rest_framework import serializers, status
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from web.models import (
    TRANSLATIONS,
    FacetteSelection,
    LanguageFeedback,
    MetaFilterValue,
    Session,
    SessionVersion,
)
from web.util import get_translation_haystack


def is_language_present(lang):
    found_lang = False
    for lang_tuple in AVAILABLE_LANGUAGES:
        lang_key = lang_tuple[0]
        if lang_key == lang:
            found_lang = True
            break
    return found_lang


class MetaTagsSerializer(serializers.Serializer):
    base_url = serializers.CharField(default=FRONTEND_URL)
    name = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    def get_language_codes(self, _: None) -> Dict[str, str]:
        result = {}
        for lang in AVAILABLE_LANGUAGES:
            result[lang[0]] = lang[1]
        return result

    def get_logo(self, _: None) -> str:
        return KUUSI_LOGO

    def get_name(self, _: None) -> str:
        return KUUSI_NAME

    def get_icon(self, _: None) -> str:
        return KUUSI_ICON

    def get_meta(self, _: None) -> Dict[str, Any]:
        tags = KUUSI_META_TAGS.copy()
        # TODO: Make more dynamic
        lang = self.context["lang"]
        if not lang:
            lang = DEFAULT_LANGUAGE_CODE
        if lang not in TRANSLATIONS:
            lang = DEFAULT_LANGUAGE_CODE
        if "DESCRIPTION_TEXT" in TRANSLATIONS[lang]:
            tags["og:description"] = TRANSLATIONS[lang]["DESCRIPTION_TEXT"]
            tags["twitter:description"] = TRANSLATIONS[lang]["DESCRIPTION_TEXT"]
        # Redundant with below serializer
        tags["og:locale"] = lang
        return tags


class MetaTagViewset(ListModelMixin, GenericViewSet):
    serializer_class = MetaTagsSerializer

    @extend_schema(
        description="Return the list of configured meta tags",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=MetaTagsSerializer,
                description="The list of meta tags available to use",
            ),
        },
        parameters=[
            OpenApiParameter(
                "lang",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="The language code to translate this values",
                required=False,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        lang = request.query_params.get("lang")
        serializer = MetaTagsSerializer({}, many=False)
        serializer.context["lang"] = lang

        return Response(serializer.data)


class SessionSerializer(serializers.ModelSerializer, MetaTagsSerializer):
    session_origin = serializers.SerializerMethodField()
    language_codes = serializers.SerializerMethodField()
    language_values = serializers.SerializerMethodField()
    default_language_values = serializers.SerializerMethodField()
    is_language_rtl = serializers.SerializerMethodField()
    test_count = serializers.SerializerMethodField()
    imprint_data = serializers.SerializerMethodField()
    privacy_data = serializers.SerializerMethodField()
    default_language = serializers.SerializerMethodField()
    is_translation_mode_enabled = serializers.SerializerMethodField()
    is_feedback_mode_enabled = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = (
            "id",
            "result_id",
            "language_code",
            "default_language",
            "language_codes",
            "session_origin",
            "started",
            "version",
            "base_url",
            "language_values",
            "default_language_values",
            "is_language_rtl",
            "name",
            "logo",
            "meta",
            "icon",
            "test_count",
            "imprint_data",
            "privacy_data",
            "is_translation_mode_enabled",
            "is_feedback_mode_enabled"
        )
    def get_is_translation_mode_enabled(self, _: None) -> bool:
        return ENABLE_TRANSLATION_MODE

    def get_is_feedback_mode_enabled(self, _: None) -> bool:
        return ENABLE_FEEDBACK_MODE

    def get_default_language(self, _: None) -> str:
        return DEFAULT_LANGUAGE_CODE

    def get_session_origin(self, obj: Session) -> str | None:
        return obj.session_origin.result_id if obj.session_origin else None

    def get_meta(self, obj: Session) -> Dict[str, Any]:
        meta = KUUSI_META_TAGS.copy()
        meta["og:locale"] = obj.language_code
        return meta

    def get_test_count(self, _) -> int:
        return SESSION_NUMBER_OFFSET

    def get_imprint_data(self, _) -> str:
        return IMPRINT

    def get_privacy_data(self, _) -> str:
        return PRIVACY

    def get_is_language_rtl(self, obj: Session) -> bool:
        return obj.language_code in RTL_LANGUAGES

    def get_language_values(self, obj: Session) -> Dict[str, str]:
        return get_translation_haystack(TRANSLATIONS, obj.language_code)

    def get_default_language_values(self, obj: Session) -> Dict[str, str]:
        return get_translation_haystack(TRANSLATIONS, DEFAULT_LANGUAGE_CODE)


class SessionVersionSerializer(serializers.ModelSerializer):
    text = serializers.SerializerMethodField()

    class Meta:
        model = SessionVersion
        fields = "__all__"

    def get_text(self, obj: SessionVersion) -> str:
        session: Session = self.context["session"]
        return obj.__("description", session.language_code)


class SessionViewSet(ViewSet):
    serializer_class = Session
    queryset = Session.objects.all()

    @extend_schema(
        request=None,
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="A result id to retrieve",
                required=True,
            ),
        ],
        responses={
            status.HTTP_200_OK: SessionSerializer,
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description="Invalid result_id provided"
            ),
        },
    )
    def retrieve(self, request, pk=None):
        queryset = Session.objects.all()
        session = get_object_or_404(queryset, result_id=pk)
        serializer = SessionSerializer(session)
        return Response(serializer.data)

    @extend_schema(
        request=None,
        description="Update a session after initial creation due to language or version switch",
        parameters=[
            OpenApiParameter(
                "result_id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="The result_id to use. Must be a valid reference to a Session object",
                required=True,
            ),
            OpenApiParameter(
                "version_id",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="The session version to use. Must be a valid reference to a Session object",
                required=False,
            ),
            OpenApiParameter(
                "lang",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="The language code to translate this values",
                required=False,
            ),
        ],
        responses={
            status.HTTP_200_OK: SessionSerializer,
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description="Invalid id or result_id provided"
            ),
            status.HTTP_406_NOT_ACCEPTABLE: OpenApiResponse(
                description="Invalid version_id provided"
            ),
        },
    )
    def partial_update(self, request, pk=None):
        lang = request.query_params.get("lang")
        if not is_language_present(lang):
            lang = DEFAULT_LANGUAGE_CODE
        version_id = request.query_params.get("version_id")
        version: SessionVersion | None = None
        if version_id:
            versions = SessionVersion.objects.filter(pk=version_id)
            if versions.first() is None:
                return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                version = versions[0]

        sessions = Session.objects.filter(pk=pk)

        session = sessions.first()
        if not session:
            return Response(status=status.HTTP_404_NOT_FOUND)

        result_id = request.query_params.get("result_id")
        if session.result_id != result_id:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # TODO: This is a side effect. Find something more elegant
        if session.language_code != lang:
            LanguageFeedback.objects.filter(session=session).delete()

        session.language_code = lang
        # TODO: Fix typing warning
        # Error complains about version not being able to be set, which should not be the case
        session.version = version  # type: ignore
        session.save()

        serializer = SessionSerializer(session)
        return Response(serializer.data)

    @extend_schema(
        request=None,
        parameters=[
            OpenApiParameter(
                "lang",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="The language code to translate this values",
                required=True,
            ),
            OpenApiParameter(
                "result_id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="A result id to copy the results from",
                required=False,
            ),
            OpenApiParameter(
                "user_agent",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="An optional user-agent header value for statistics",
                required=False,
            ),
            OpenApiParameter(
                "referrer",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="An optional referrer header value for statistics",
                required=False,
            ),
        ],
        responses={
            status.HTTP_200_OK: SessionSerializer,
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description="Invalid result_id provided"
            ),
            status.HTTP_406_NOT_ACCEPTABLE: OpenApiResponse(
                description="Invalid version_id provided"
            ),
        },
    )
    def create(self, request):
        lang = request.query_params.get("lang")
        if not is_language_present(lang):
            lang = DEFAULT_LANGUAGE_CODE
        old_result_id = request.query_params.get("result_id")
        referrer = request.query_params.get("referrer")
        user_agent = request.query_params.get("user_agent")

        session = self.get_fresh_session(lang, user_agent, referrer)
        old_session = None
        if old_result_id:
            old_sessions = Session.objects.filter(result_id=old_result_id)
            if old_sessions.first() is None:
                return Response(status=status.HTTP_404_NOT_FOUND)
            else:
                old_session = old_sessions.first()
            if not session.session_origin:
                # copy old meta values
                values = MetaFilterValue.objects.filter(session=old_session)

                value: MetaFilterValue
                for value in values:
                    value.pk = None
                    value.session = session
                    value.save()

                # copy old selections
                selections = FacetteSelection.objects.filter(session=old_session)
                selection: FacetteSelection
                for selection in selections:
                    # prevent double copies
                    if (
                        FacetteSelection.objects.filter(
                            session=session, facette=selection.facette
                        ).count()
                        == 0
                    ):
                        selection.pk = None
                        selection.session = session
                        selection.save()
                # TODO: Find reason for typing error
                # Find way to remove # type: ignore
                session.session_origin = old_session  # type: ignore
                session.save()
        if old_session:
            self.clone_selections(old_session, session)
        serializer = SessionSerializer(session)
        return Response(serializer.data)

    def clone_selections(self, old_session: Session, session: Session) -> bool:
        if session.session_origin is not None:
            return False
        selections = FacetteSelection.objects.filter(session=old_session)
        selection: FacetteSelection
        for selection in selections:
            # prevent double copies
            if (
                FacetteSelection.objects.filter(
                    session=session, facette=selection.facette
                ).count()
                == 0
            ):
                selection.pk = None
                selection.session = session
                selection.save()
        # TODO: Find reason for typing error
        # Find way to remove # type: ignore
        session.session_origin = old_session  # type: ignore
        session.save()
        return True

    def get_fresh_session(
        self, language_code: str, user_agent: str, referrer: str
    ) -> Session:
        """
        Create a new session.
        """
        session = Session()
        session.user_agent = user_agent
        session.referrer = referrer
        session.language_code = language_code
        session.referrer = referrer
        session.save()
        return session
