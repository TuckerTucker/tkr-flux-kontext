# Edit or create an image with Flux Kontext Pro

## OpenAPI

````yaml openapi.json post /v1/flux-kontext-pro
paths:
  path: /v1/flux-kontext-pro
  method: post
  servers:
    - url: https://api.us1.bfl.ai
      description: BFL API
  request:
    security:
      - title: APIKeyHeader
        parameters:
          query: {}
          header:
            x-key:
              type: apiKey
          cookie: {}
    parameters:
      path: {}
      query: {}
      header: {}
      cookie: {}
    body:
      application/json:
        schemaArray:
          - type: object
            properties:
              prompt:
                allOf:
                  - type: string
                    title: Prompt
                    description: Text prompt for image generation.
                    example: ein fantastisches bild
              input_image:
                allOf:
                  - anyOf:
                      - type: string
                      - type: 'null'
                    title: Input Image
                    description: Base64 encoded image to use with Kontext.
              seed:
                allOf:
                  - anyOf:
                      - type: integer
                      - type: 'null'
                    title: Seed
                    description: Optional seed for reproducibility.
                    example: 42
              aspect_ratio:
                allOf:
                  - anyOf:
                      - type: string
                      - type: 'null'
                    title: Aspect Ratio
                    description: Aspect ratio of the image between 21:9 and 9:21
              output_format:
                allOf:
                  - anyOf:
                      - $ref: '#/components/schemas/OutputFormat'
                      - type: 'null'
                    description: >-
                      Output format for the generated image. Can be 'jpeg' or
                      'png'.
                    default: png
              webhook_url:
                allOf:
                  - anyOf:
                      - type: string
                        maxLength: 2083
                        minLength: 1
                        format: uri
                      - type: 'null'
                    title: Webhook Url
                    description: URL to receive webhook notifications
              webhook_secret:
                allOf:
                  - anyOf:
                      - type: string
                      - type: 'null'
                    title: Webhook Secret
                    description: Optional secret for webhook signature verification
              prompt_upsampling:
                allOf:
                  - type: boolean
                    title: Prompt Upsampling
                    description: >-
                      Whether to perform upsampling on the prompt. If active,
                      automatically modifies the prompt for more creative
                      generation.
                    default: false
              safety_tolerance:
                allOf:
                  - type: integer
                    maximum: 6
                    minimum: 0
                    title: Safety Tolerance
                    description: >-
                      Tolerance level for input and output moderation. Between 0
                      and 6, 0 being most strict, 6 being least strict.
                    default: 2
                    example: 2
            required: true
            title: FluxKontextProInputs
            refIdentifier: '#/components/schemas/FluxKontextProInputs'
            requiredProperties:
              - prompt
        examples:
          example:
            value:
              prompt: ein fantastisches bild
              input_image: <string>
              seed: 42
              aspect_ratio: <string>
              output_format: jpeg
              webhook_url: <string>
              webhook_secret: <string>
              prompt_upsampling: false
              safety_tolerance: 2
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              id:
                allOf:
                  - type: string
                    title: Id
              polling_url:
                allOf:
                  - type: string
                    title: Polling Url
            title: AsyncResponse
            refIdentifier: '#/components/schemas/AsyncResponse'
            requiredProperties:
              - id
              - polling_url
          - type: object
            properties:
              id:
                allOf:
                  - type: string
                    title: Id
              status:
                allOf:
                  - type: string
                    title: Status
              webhook_url:
                allOf:
                  - type: string
                    title: Webhook Url
            title: AsyncWebhookResponse
            refIdentifier: '#/components/schemas/AsyncWebhookResponse'
            requiredProperties:
              - id
              - status
              - webhook_url
        examples:
          example:
            value:
              id: <string>
              polling_url: <string>
        description: Successful Response
    '422':
      application/json:
        schemaArray:
          - type: object
            properties:
              detail:
                allOf:
                  - items:
                      $ref: '#/components/schemas/ValidationError'
                    type: array
                    title: Detail
            title: HTTPValidationError
            refIdentifier: '#/components/schemas/HTTPValidationError'
        examples:
          example:
            value:
              detail:
                - loc:
                    - <string>
                  msg: <string>
                  type: <string>
        description: Validation Error
  deprecated: false
  type: path
components:
  schemas:
    OutputFormat:
      type: string
      enum:
        - jpeg
        - png
      title: OutputFormat
    ValidationError:
      properties:
        loc:
          items:
            anyOf:
              - type: string
              - type: integer
          type: array
          title: Location
        msg:
          type: string
          title: Message
        type:
          type: string
          title: Error Type
      type: object
      required:
        - loc
        - msg
        - type
      title: ValidationError

````