{{- define "podcast-content-agent.name" -}}
podcast-content-agent
{{- end }}

{{- define "podcast-content-agent.fullname" -}}
{{ .Release.Name }}-{{ include "podcast-content-agent.name" . }}
{{- end }}

{{- define "podcast-content-agent.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "podcast-content-agent.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}