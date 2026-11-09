============================
``neutrons_standard.config``
============================

.. automodule:: neutrons_standard.config
   :no-members:

See :doc:`../config` for a usage guide.

Configuration
=============

.. py:data:: neutrons_standard.config.Config
   :type: _Config

   The application-wide :class:`_Config` singleton instance.

.. autoclass:: neutrons_standard.config._Config
   :members:
   :undoc-members:

Resources
=========

.. py:data:: neutrons_standard.config.Resource
   :type: _Resource

   The application-wide :class:`_Resource` instance.

.. autoclass:: neutrons_standard.config._Resource
   :members:
   :undoc-members:

Deployment environments
=======================

.. autoclass:: neutrons_standard.config.DeployEnvEnum
   :members:
   :undoc-members:

.. autofunction:: neutrons_standard.config.is_test_env

Dictionary utilities
====================

.. autofunction:: neutrons_standard.config.merge_dicts

.. autofunction:: neutrons_standard.config.deep_update
