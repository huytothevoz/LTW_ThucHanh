<?php

namespace App\Support;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Lang;
use Twig\Environment;
use Twig\Loader\FilesystemLoader;
use Twig\TwigFunction;

class TwigRenderer
{
    private Environment $twig;

    public function __construct()
    {
        $loader = new FilesystemLoader(base_path('templates'));
        $this->twig = new Environment($loader, [
            'autoescape' => 'html',
            'cache' => false,
            'strict_variables' => false,
        ]);
        $this->twig->addFunction(new TwigFunction('t', fn (string $key): string => Lang::get($key)));
        $this->twig->addFunction(new TwigFunction('asset', function (string $path): string {
            $normalized = ltrim($path, '/');
            $fullPath = base_path($normalized);
            $v = file_exists($fullPath) ? filemtime($fullPath) : time();
            return '/' . $normalized . '?v=' . $v;
        }));
    }

    public function render(Request $request, string $template, array $context = []): string
    {
        $request->session()->regenerateToken();
        $context += [
            'user' => $request->attributes->get('current_user'),
            'prefs' => $request->attributes->get('preferences', []),
            'locale' => $request->attributes->get('locale', 'vi'),
            'active_page' => null,
            'csrf' => csrf_token(),
            'db_driver' => env('DB_CONNECTION', 'mysql'),
        ];

        return $this->twig->render($template, $context);
    }
}
