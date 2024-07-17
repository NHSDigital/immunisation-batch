#AWS Lambda Python image. should it be 3.10 or 3.8?
FROM public.ecr.aws/lambda/python:3.10 as base

#copy lambda code
COPY router_lambda_function.py ${LAMBDA_TASK_ROOT}

#Run lambda function
CMD[router_lambda_function.lambda_handler]