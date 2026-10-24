# SUBTERRA — Music-to-Film Engine v0.1.0

Programa local para transformar uma música em um filme procedural com estética **Techno Underground**. Esta primeira versão já executa o ciclo completo:

1. diagnostica hardware e FFmpeg;
2. analisa áudio em domínio temporal, espectral, harmônico e rítmico;
3. estima BPM, tom, batidas, energia, brilho, textura e estrutura por seções;
4. cria uma narrativa visual com seed reproduzível;
5. combina imagens ou vídeos fornecidos pelo usuário;
6. renderiza um filme com a mesma duração da música;
7. incorpora o áudio e exporta MP4, MKV ou AVI.

Tudo roda localmente. Não há API paga, envio de música para servidores nem dependência obrigatória de IA.

## Por que o núcleo não é apenas TouchDesigner

O TouchDesigner é excelente para prototipagem e performance em tempo real, mas sua licença Non-Commercial gratuita limita a resolução a 1280x1280. Isso impede 1080x1920, 2K e 4K como solução universal gratuita. O SUBTERRA usa Python + OpenCV + FFmpeg como núcleo livre e poderá receber uma ponte TouchDesigner em uma fase posterior.

## Instalação no Windows

Pré-requisitos:

- Windows 10/11;
- Python 3.11 ou 3.12;
- FFmpeg disponível no `PATH`;
- pelo menos 8 GB de RAM; 16 GB recomendados.

Passos:

1. Execute `INSTALAR_WINDOWS.bat`.
2. Execute `DIAGNOSTICO_WINDOWS.bat`.
3. Abra `ABRIR_SUBTERRA.bat`.
4. Selecione a música, a saída, a resolução e as mídias base.
5. Use primeiro `draft` ou `720p` para validar a estética.

## Linha de comando

Diagnóstico:

```powershell
.venv\Scripts\python.exe subterra.py diagnose --output hardware_report.json
```

Análise:

```powershell
.venv\Scripts\python.exe subterra.py analyze "musica.wav" --workdir projeto_analise
```

Render básico:

```powershell
.venv\Scripts\python.exe subterra.py render "musica.wav" "output\filme.mp4" --resolution 1080p --render-scale 0.75
```

Render vertical com mídias base:

```powershell
.venv\Scripts\python.exe subterra.py render "musica.flac" "output\reel.mp4" `
  --resolution reel `
  --media "media\foto.png" `
  --media "media\video.mp4" `
  --seed 984512 `
  --style auto
```

Resolução personalizada:

```powershell
.venv\Scripts\python.exe subterra.py render "musica.mp3" "output\custom.mkv" --width 1400 --height 2200
```

Teste rápido de 15 segundos:

```powershell
.venv\Scripts\python.exe subterra.py render "musica.wav" "output\preview.mp4" --resolution 720p --preview-seconds 15 --render-scale 0.5
```

## Presets de resolução

- `draft`: 640x360
- `720p`: 1280x720
- `1080p`: 1920x1080
- `2k`: 2560x1440
- `4k`: 3840x2160
- `reel` / `tiktok`: 1080x1920
- `square`: 1080x1080
- `cinema_2k`: 2048x1080
- `cinema_4k`: 4096x2160

## Estilos visuais

- `auto`: muda a linguagem por seção da música;
- `industrial_tunnel`;
- `vector_field`;
- `particle_ritual`;
- `pixel_corruption`;
- `halftone_signal`;
- `machine_vision`;
- `liquid_feedback`.

## Seed e variação

Sem `--seed`, cada render recebe uma semente aleatória. Com a mesma música, configurações e seed, o plano visual é reproduzível. Para uma história nova, gere uma seed nova na interface.

## Áudio

`--audio-mode preserve` é o padrão e evita alterar destrutivamente o master original. `--audio-mode normalize` aplica normalização de loudness com limite de true peak por FFmpeg. A normalização automática não substitui mixagem/masterização humana; ela serve para conformidade e consistência de entrega.

## Segurança visual

O strobe é limitado por padrão. Pessoas sensíveis a flashes devem usar `--strobe 0`. A aplicação nunca deve prometer segurança médica absoluta; revise o filme antes da publicação ou exibição pública.

## Artefatos do projeto

Para cada filme, a pasta de trabalho contém:

- `analysis.json`: resumo musical;
- `features.npz`: curvas de controle ao longo do tempo;
- `story.json`: narrativa visual e cenas;
- `render_config.json`: parâmetros do render;
- `report.html`: relatório legível no navegador.

## Limites desta versão

- A transcrição de letras ainda não está integrada no instalador principal.
- Separação de stems e LLM local são planejados como módulos opcionais, porque aumentam muito consumo de memória e possuem requisitos/licenças de pesos que precisam ser validados por modelo.
- O render é offline e baseado principalmente em CPU/OpenCV; 4K pode ser demorado.
- A interpretação narrativa é procedural, não uma compreensão cinematográfica completa da letra.

## Próximas fases planejadas

- stem separation opcional;
- Whisper/whisper.cpp local para letra com timestamps;
- planejador semântico local via modelo Apache-2.0 selecionado pelo diagnóstico;
- shaders GPU Vulkan/OpenGL;
- editor visual de cenas e curvas;
- exportação de canais para TouchDesigner/OSC/CSV;
- templates adicionais e gerenciamento de biblioteca de mídia;
- render por fila, checkpoints e retomada.
