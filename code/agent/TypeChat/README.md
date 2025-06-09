# TypeChat
This is an implementation of [Microsoft's TypeChat](https://microsoft.github.io/TypeChat/) in Python. The purpose of this repository is to enable typed (JSON) outputs for any LLM that can, at a minium, understand code and language. With a few optimizations in contrast to Microsoft's original TypeScript implementation, this is a mostly truthful re-implementation in Python. 

Currently, the TypeChat implementation can work with the following APIs:
- OpenAI's GPT models
- FastChat's OpenAI-esque API
- Ollama's REST Api

If the model supports it, you will be able to use JSON mode. If you want to utilize Ollama, please install and serve the respective model locally. A demo for each API is provided in the example.

## Utilizing TypeChat

In order to run the code, please install the following packages in their most recent version:

```
pip install openai
```
Additionally, you will need to install the TypeScript compiler, which has an executable called _tsc_. 

```
conda install conda-forge::typescript
```

If that doesn't work for your platform, please look up how to install tsc for your platform.

After successful installation, an example is provided in the _example.py_ file, demonstrating a simple sentiment classification task utilizing types. In order to run this example, please create a _keys.py_ file next to the _example.py_ file with your respective API keys and organization string provided through your OpenAI account. The file should look as follows:

```
API_KEY="<your_key>"
ORG_KEY="<your_organization>"
```

After providing the necessary keys, you can try the system by running
```
python example.py
```

This will run the example request and (hopefully) print a message saying that the sentiment is positive. In the example, you can choose which type of API you want to use.

## Current Limitations
The following are the current limitations:
- You can only run one instance of TypeChat. As the system writes files to the disk that are compiled with TypeScript, multiple instances of TypeChat running concurrently could potentially overwrite each-other's files.
- TypeChat requires the use of an LLM that is capable of understanding language and code. However, you don't need explicit coding models, as not much code knowledge is required to understand the schemas, but some, particularly small models, are unable to comprehend the TypeScript schema. In such case, they will not be able to generate any useful JSON. 
    - Note: The best model to use for this remains GPT-4, however, for simple schemas, we saw success with GPT-3.5 and larger LLama-2 models, as well as the rather small Starling model. 