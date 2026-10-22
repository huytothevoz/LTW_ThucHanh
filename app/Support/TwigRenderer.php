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
        $this->twig->addFunction(new TwigFunction('asset', fn (string $path): string => '/'.ltrim($path, '/')));
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
        ];

        return $this->twig->render($template, $context);
    }
}
