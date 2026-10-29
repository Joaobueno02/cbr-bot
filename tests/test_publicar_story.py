"""Publicação simulada, sem token, rede ou arquivos da fila real."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bot import publicar as p


class StoryAutomatico(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.arq = self.raiz / 'post.json'
        (self.raiz / 'story.jpg').write_bytes(b'arte simulada')
        self.post = {'status': 'publicar', 'revisao': {'aprovado': True},
                     'legenda': 'Notícia de teste', 'hashtags': ['a', 'b', 'c', 'd', 'e'],
                     'render': {'artes': [{'arquivo': 'arte-1.jpg'}], 'story': 'story.jpg'}}
        self.estado = {'publicados': 0}
        for nome in ('REGISTRO', 'PENDENTES', 'AVISOS', 'RODIZIO_REG'):
            self.iniciar(patch.object(p, nome, self.raiz / nome))
        self.iniciar(patch.dict(p.CONFIG, {'publicacao_ativa': True, 'story_automatico': True}))
        self.iniciar(patch.object(p, 'decidir_collab', return_value=[]))
        self.iniciar(patch.object(p, 'escolher_musica', return_value=(None, None)))
        self.dormir = self.iniciar(patch.object(p.time, 'sleep'))
        self.api = self.iniciar(patch.object(p, 'chamar', side_effect=self.responder))
        self.containers = {}
        self.envios = []
        self.falha_story = None
        self.status_story = 'FINISHED'

    def iniciar(self, remendo):
        obj = remendo.start()
        self.addCleanup(remendo.stop)
        return obj

    def responder(self, metodo, caminho, **params):
        if metodo == 'POST' and caminho.endswith('/media'):
            cid = str(len(self.containers) + 1)
            self.containers[cid] = params
            return {'id': cid}
        if metodo == 'POST' and caminho.endswith('/media_publish'):
            cid = params['creation_id']
            self.envios.append(cid)
            if self.containers[cid].get('media_type') == 'STORIES':
                salvo = json.loads(self.arq.read_text())
                self.assertEqual(salvo['status'], 'publicado')
                self.assertTrue(salvo['publicacao']['media_id'])
                self.assertEqual(salvo['publicacao']['story']['container_id'], cid)
                self.assertTrue(salvo['publicacao']['story']['envio_iniciado'])
                if self.falha_story:
                    raise self.falha_story
            return {'id': 'mid-' + cid}
        if params.get('fields') == 'status_code':
            return {'status_code': self.status_story if caminho in self.envios else 'FINISHED'}
        if params.get('fields') == 'permalink':
            return {'permalink': 'https://exemplo.test/post'}
        if caminho.endswith('/media'):
            return {'data': []}
        raise AssertionError((metodo, caminho, params))

    def executar(self):
        self.arq.write_text(json.dumps(self.post))
        p.processar(self.arq, self.estado)
        self.post = json.loads(self.arq.read_text())

    def test_sucesso_todos_formatos(self):
        for formato in ('unico', 'reels', 'carrossel'):
            with self.subTest(formato=formato):
                self.post.pop('publicacao', None)
                self.post['status'] = 'publicar'
                self.post['formato'] = 'carrossel' if formato == 'carrossel' else 'unico'
                self.post['reels'] = formato == 'reels'
                self.post['render']['reels'] = {'video': 'reels.mp4', 'capa': 'capa.jpg'}
                self.post['render']['artes'] = [{'arquivo': 'arte-1.jpg'}] * (2 if formato == 'carrossel' else 1)
                self.estado = {'publicados': 0}
                self.executar()
                self.assertEqual(self.post['status'], 'publicado')
                story = self.post['publicacao']['story']
                self.assertTrue(story['media_id'])
                self.assertEqual(self.containers[story['container_id']], {
                    'media_type': 'STORIES', 'image_url': p.url_arte(self.raiz.name, 'story.jpg')})
                self.assertEqual(self.estado['publicados'], 1)
                self.assertTrue(any(59 <= c.args[0] <= 60 for c in self.dormir.call_args_list))

    def test_falha_story_preserva_feed_e_nao_duplica(self):
        self.falha_story = p.ErroAPI('4/2207051: aviso simulado')
        self.executar()
        self.assertEqual(self.post['status'], 'publicado')
        self.assertIn('2207051', self.post['publicacao']['story']['erro'])
        aviso = json.loads(p.AVISOS.read_text())
        self.assertEqual(aviso['tipo'], 'story')
        self.post['status'] = 'publicar'
        self.executar()
        self.assertEqual(len(self.envios), 2)
        self.assertEqual(self.estado['publicados'], 1)
        self.assertEqual(self.post['status'], 'publicado')

    def test_nova_tentativa_sucesso_nao_duplica(self):
        self.executar()
        self.post['status'] = 'publicar'
        self.api.reset_mock()
        self.executar()
        self.api.assert_not_called()
        self.assertEqual(self.estado['publicados'], 1)

    def test_aviso_mas_container_publicado(self):
        self.falha_story = p.ErroAPI('4/2207051: aviso simulado')
        self.status_story = 'PUBLISHED'
        self.executar()
        story = self.post['publicacao']['story']
        self.assertTrue(story['publicado'])
        self.assertNotIn('erro', story)
        self.assertTrue(json.loads(p.AVISOS.read_text())['publicado'])

    def test_retomada_consulta_container_publicado(self):
        self.falha_story = TimeoutError('tempo esgotado')
        self.executar()
        self.status_story = 'PUBLISHED'
        self.post['status'] = 'publicar'
        self.executar()
        self.assertTrue(self.post['publicacao']['story']['publicado'])
        self.assertEqual(len(self.envios), 2)

    def test_desligado(self):
        p.CONFIG['story_automatico'] = False
        self.executar()
        self.assertEqual(len(self.envios), 1)
        self.assertNotIn('story', self.post['publicacao'])

    def test_ativado_por_padrao(self):
        del p.CONFIG['story_automatico']
        self.executar()
        self.assertTrue(self.post['publicacao']['story']['publicado'])

    def test_sem_story(self):
        del self.post['render']['story']
        self.executar()
        self.assertEqual(len(self.envios), 1)

    def test_arquivo_ausente_nao_afeta_feed(self):
        (self.raiz / 'story.jpg').unlink()
        self.executar()
        self.assertEqual(self.post['status'], 'publicado')
        self.assertIn('erro', self.post['publicacao']['story'])
        self.assertEqual(len(self.envios), 1)

    def test_falha_registro_aviso_nao_afeta_feed(self):
        self.falha_story = p.ErroAPI('4/2207051: aviso simulado')
        with patch.object(p, 'AVISOS', self.raiz / 'ausente' / 'avisos.jsonl'):
            self.executar()
        self.assertEqual(self.post['status'], 'publicado')
        self.assertIn('aviso_registro', self.post['publicacao']['story'])

    def test_falha_feed_nao_publica_story(self):
        self.api.side_effect = p.ErroAPI('feed indisponível')
        self.executar()
        self.assertEqual(self.post['status'], 'erro_publicacao')
        self.assertNotIn('story', self.post['publicacao'])
        self.assertEqual(self.envios, [])

    def test_intervalo_feed_preservado(self):
        self.estado['ultima_publicacao'] = p.agora()
        self.executar()
        self.assertEqual(self.post['status'], 'agendado')
        self.api.assert_not_called()

    def test_publicacao_desligada(self):
        p.CONFIG['publicacao_ativa'] = False
        self.executar()
        self.api.assert_not_called()
        self.assertEqual(self.post['status'], 'simulado')


if __name__ == '__main__':
    unittest.main()
