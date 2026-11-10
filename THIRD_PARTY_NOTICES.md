# Componentes e repertório

A licença MIT na raiz cobre o código próprio do Tessera Piano.

| Componente | Licença | Origem |
| --- | --- | --- |
| Python | PSF e licenças incluídas no runtime | https://www.python.org/ |
| Qt / PySide6 / Shiboken | LGPLv3, com bibliotecas compartilhadas na distribuição | https://www.qt.io/licensing/open-source-lgpl-obligations |
| Mido | MIT | https://github.com/mido/mido |
| cryptography | Apache 2.0 ou BSD 3-Clause | https://github.com/pyca/cryptography |
| packaging | Apache 2.0 ou BSD 2-Clause | https://github.com/pypa/packaging |
| cffi | MIT | https://cffi.readthedocs.io/ |
| pycparser | BSD 3-Clause | https://github.com/eliben/pycparser |

Os textos de licença acompanham o instalador na pasta `licenses`. As bibliotecas Qt permanecem separadas do executável e podem ser substituídas por versões compatíveis. Fontes das versões distribuídas de Qt e PySide estão disponíveis nos repositórios oficiais: [Qt](https://code.qt.io/cgit/qt/) e [PySide](https://code.qt.io/cgit/pyside/pyside-setup.git/), versão 6.12.0. Não são usadas modificações locais nessas bibliotecas.

Os MIDIs, arquivos LilyPond e conversões do repertório mantêm os créditos e as licenças de cada edição. Consulte [atribuições do repertório](src/tessera_piano/resources/REPERTOIRE_LICENSES.txt) e as [fontes musicais](repertoire), que incluem os arquivos `CREDITOS.txt`. A edição de Sonata ao Luar e sua conversão são CC BY-SA 2.5; as demais edições indicadas como domínio público conservam essa indicação. A música Entre Órbitas faz parte do repertório original do projeto.

PyInstaller e Inno Setup são ferramentas de construção; seus termos e exceções de distribuição estão disponíveis nos respectivos projetos. Os ícones e a identidade visual são os recursos originais fornecidos com o Tessera Piano.

## Motor musical opcional

O pacote separado usa [Pianist Transformer](https://github.com/yhj137/PianistTransformer), de Hong-Jie You e colaboradores, e os pesos [pianist-transformer-rendering](https://huggingface.co/yhj137/pianist-transformer-rendering), ambos declarados sob Apache-2.0. Código fixado em `747df2d12291e37f6638b39f1b71517e579ad48c`; pesos em `8f1568201d1ec035c73939d5a67c5168c0b80221`. Consulte a licença e `NOTICE.txt` no pacote. Referência: *Pianist Transformer: Towards Expressive Piano Performance Rendering via Scalable Self-Supervised Pre-Training*, ICML 2026, [arXiv:2512.02652](https://arxiv.org/abs/2512.02652).

Python e as dependências do runtime mantêm suas licenças no pacote. O código próprio de integração do Tessera permanece MIT. O Chroma usa a API REST do serviço Razer instalado pelo usuário; DLLs e software da Razer não são redistribuídos.
