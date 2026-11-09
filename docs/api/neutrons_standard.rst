=====================
``neutrons_standard``
=====================

.. automodule:: neutrons_standard
   :no-members:

Client packages must register their name with :func:`init` before accessing :data:`neutrons_standard.Config`.

.. autofunction:: neutrons_standard.init

.. py:data:: neutrons_standard.Spec
   :type: _Spec

   The package-level settings instance; see :class:`_Spec`.

.. autoclass:: neutrons_standard._Spec
   :members:
   :undoc-members:

.. py:data:: neutrons_standard.Config
   :type: neutrons_standard.config._Config

   The configuration singleton, loaded lazily on first access; see :class:`neutrons_standard.config._Config`.
