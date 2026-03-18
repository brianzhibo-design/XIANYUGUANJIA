from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.modules.listing.image_generator import (
    DEFAULT_OUTPUT_DIR,
    VIEWPORT,
    _render_html_to_png,
    generate_product_images,
    get_available_categories,
)


class TestGetAvailableCategories:
    def test_returns_list(self):
        result = get_available_categories()
        assert isinstance(result, list)
        assert len(result) > 0
        keys = {item["key"] for item in result}
        assert "express" in keys
        assert "game" in keys


class TestGenerateProductImages:
    @pytest.mark.asyncio
    async def test_invalid_category(self):
        result = await generate_product_images(category="nonexistent_xyz")
        assert result == []

    @pytest.mark.asyncio
    async def test_default_params_list(self, tmp_path):
        with patch("src.modules.listing.image_generator.render_template", return_value="<html>ok</html>"):
            with patch("src.modules.listing.image_generator._render_html_to_png", new_callable=AsyncMock) as mock_render:
                result = await generate_product_images(category="express", output_dir=tmp_path)
                assert mock_render.call_count == 1
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_multiple_params(self, tmp_path):
        with patch("src.modules.listing.image_generator.render_template", return_value="<html>ok</html>"):
            with patch("src.modules.listing.image_generator._render_html_to_png", new_callable=AsyncMock) as mock_render:
                params_list = [{"title": "A"}, {"title": "B"}]
                result = await generate_product_images(category="recharge", params_list=params_list, output_dir=tmp_path)
                assert mock_render.call_count == 2
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_render_failure(self, tmp_path):
        with patch("src.modules.listing.image_generator.render_template", return_value="<html>ok</html>"):
            with patch("src.modules.listing.image_generator._render_html_to_png", new_callable=AsyncMock) as mock_render:
                mock_render.side_effect = Exception("render failed")
                result = await generate_product_images(category="game", params_list=[{}], output_dir=tmp_path)
                assert result == []

    @pytest.mark.asyncio
    async def test_template_returns_none(self, tmp_path):
        with patch("src.modules.listing.image_generator.render_template", return_value=None):
            result = await generate_product_images(category="express", output_dir=tmp_path)
            assert result == []

    @pytest.mark.asyncio
    async def test_default_output_dir(self):
        with patch("src.modules.listing.image_generator.render_template", return_value="<html>ok</html>"):
            with patch("src.modules.listing.image_generator._render_html_to_png", new_callable=AsyncMock):
                with patch.object(Path, "mkdir"):
                    result = await generate_product_images(category="express")
                    assert len(result) == 1

    @pytest.mark.asyncio
    async def test_category_sanitization(self, tmp_path):
        with patch("src.modules.listing.image_generator.list_templates") as mock_lt:
            mock_lt.return_value = [{"key": "a_b"}]
            with patch("src.modules.listing.image_generator.render_template", return_value="<html></html>"):
                with patch("src.modules.listing.image_generator._render_html_to_png", new_callable=AsyncMock):
                    result = await generate_product_images(category="a_b", output_dir=tmp_path)
                    assert len(result) == 1


class TestRenderHtmlToPng:
    @pytest.mark.asyncio
    async def test_drissionpage_import_error(self):
        with patch.dict("sys.modules", {"DrissionPage": None}):
            with pytest.raises((RuntimeError, ImportError)):
                await _render_html_to_png("<html></html>", Path("/tmp/test.png"))

    @pytest.mark.asyncio
    async def test_successful_render(self, tmp_path):
        mock_tab = Mock()
        mock_browser = Mock()
        mock_browser.latest_tab = mock_tab
        mock_browser.quit = Mock()

        mock_chromium_cls = Mock(return_value=mock_browser)
        mock_options_cls = Mock()
        mock_options_instance = Mock()
        mock_options_cls.return_value = mock_options_instance

        mock_dp = MagicMock()
        mock_dp.Chromium = mock_chromium_cls
        mock_dp.ChromiumOptions = mock_options_cls

        with patch.dict("sys.modules", {"DrissionPage": mock_dp}):
            await _render_html_to_png("<html>test</html>", tmp_path / "out.png")

        mock_chromium_cls.assert_called_once_with(mock_options_instance)
        assert mock_tab.get.call_count == 1
        call_args = mock_tab.get.call_args[0]
        assert call_args[0].startswith("file://")
        mock_tab.get_screenshot.assert_called_once_with(
            path=str(tmp_path / "out.png"), full_page=False
        )
        mock_browser.quit.assert_called_once()
